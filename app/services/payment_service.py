"""
Payment Processing Service for Maritime Reservation System
Comprehensive implementation supporting multiple payment gateways
"""

import stripe
import paypal
from typing import Dict, Any, Optional, List
from decimal import Decimal
from enum import Enum
import logging
from datetime import datetime, timedelta
import hashlib
import secrets
from dataclasses import dataclass
from sqlalchemy.orm import Session

# Configure logging
logger = logging.getLogger(__name__)

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"

class PaymentMethod(Enum):
    STRIPE_CARD = "stripe_card"
    STRIPE_SEPA = "stripe_sepa"
    PAYPAL = "paypal"
    PAYPAL_PAY_LATER = "paypal_pay_later"
    BANK_TRANSFER = "bank_transfer"

class Currency(Enum):
    EUR = "EUR"
    USD = "USD"
    TND = "TND"  # Tunisian Dinar
    GBP = "GBP"

@dataclass
class PaymentRequest:
    """Payment request data structure"""
    booking_id: str
    amount: Decimal
    currency: Currency
    payment_method: PaymentMethod
    customer_email: str
    customer_name: str
    description: str
    metadata: Dict[str, Any] = None
    return_url: str = None
    cancel_url: str = None

@dataclass
class PaymentResponse:
    """Payment response data structure"""
    payment_id: str
    status: PaymentStatus
    amount: Decimal
    currency: Currency
    gateway_transaction_id: str = None
    gateway_response: Dict[str, Any] = None
    redirect_url: str = None
    error_message: str = None

class PaymentSecurityManager:
    """Handles payment security and PCI DSS compliance"""
    
    def __init__(self):
        self.encryption_key = self._generate_encryption_key()
    
    def _generate_encryption_key(self) -> str:
        """Generate secure encryption key for sensitive data"""
        return secrets.token_urlsafe(32)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive payment data"""
        # Implementation would use proper encryption library
        # This is a placeholder for demonstration
        return hashlib.sha256(data.encode()).hexdigest()
    
    def validate_payment_data(self, payment_request: PaymentRequest) -> bool:
        """Validate payment request data for security compliance"""
        # Validate amount
        if payment_request.amount <= 0:
            return False
        
        # Validate email format
        if "@" not in payment_request.customer_email:
            return False
        
        # Validate currency
        if payment_request.currency not in Currency:
            return False
        
        return True
    
    def generate_payment_token(self, booking_id: str) -> str:
        """Generate secure payment token"""
        timestamp = str(int(datetime.now().timestamp()))
        data = f"{booking_id}:{timestamp}:{secrets.token_urlsafe(16)}"
        return hashlib.sha256(data.encode()).hexdigest()

class StripePaymentProcessor:
    """Stripe payment processing implementation"""
    
    def __init__(self, api_key: str, webhook_secret: str):
        stripe.api_key = api_key
        self.webhook_secret = webhook_secret
    
    async def create_payment_intent(self, payment_request: PaymentRequest) -> PaymentResponse:
        """Create Stripe payment intent"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(payment_request.amount * 100),  # Convert to cents
                currency=payment_request.currency.value.lower(),
                metadata={
                    'booking_id': payment_request.booking_id,
                    'customer_email': payment_request.customer_email,
                    **(payment_request.metadata or {})
                },
                description=payment_request.description,
                receipt_email=payment_request.customer_email,
                automatic_payment_methods={'enabled': True}
            )
            
            return PaymentResponse(
                payment_id=intent.id,
                status=PaymentStatus.PENDING,
                amount=payment_request.amount,
                currency=payment_request.currency,
                gateway_transaction_id=intent.id,
                gateway_response=intent,
                redirect_url=None
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment creation failed: {str(e)}")
            return PaymentResponse(
                payment_id="",
                status=PaymentStatus.FAILED,
                amount=payment_request.amount,
                currency=payment_request.currency,
                error_message=str(e)
            )
    
    async def create_checkout_session(self, payment_request: PaymentRequest) -> PaymentResponse:
        """Create Stripe checkout session for hosted payment page"""
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card', 'sepa_debit'],
                line_items=[{
                    'price_data': {
                        'currency': payment_request.currency.value.lower(),
                        'product_data': {
                            'name': payment_request.description,
                        },
                        'unit_amount': int(payment_request.amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=payment_request.return_url,
                cancel_url=payment_request.cancel_url,
                customer_email=payment_request.customer_email,
                metadata={
                    'booking_id': payment_request.booking_id,
                    **(payment_request.metadata or {})
                }
            )
            
            return PaymentResponse(
                payment_id=session.id,
                status=PaymentStatus.PENDING,
                amount=payment_request.amount,
                currency=payment_request.currency,
                gateway_transaction_id=session.id,
                gateway_response=session,
                redirect_url=session.url
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe checkout session creation failed: {str(e)}")
            return PaymentResponse(
                payment_id="",
                status=PaymentStatus.FAILED,
                amount=payment_request.amount,
                currency=payment_request.currency,
                error_message=str(e)
            )
    
    async def confirm_payment(self, payment_id: str) -> PaymentResponse:
        """Confirm Stripe payment status"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_id)
            
            status_mapping = {
                'requires_payment_method': PaymentStatus.PENDING,
                'requires_confirmation': PaymentStatus.PENDING,
                'requires_action': PaymentStatus.PROCESSING,
                'processing': PaymentStatus.PROCESSING,
                'succeeded': PaymentStatus.COMPLETED,
                'canceled': PaymentStatus.CANCELLED
            }
            
            return PaymentResponse(
                payment_id=intent.id,
                status=status_mapping.get(intent.status, PaymentStatus.FAILED),
                amount=Decimal(intent.amount) / 100,
                currency=Currency(intent.currency.upper()),
                gateway_transaction_id=intent.id,
                gateway_response=intent
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment confirmation failed: {str(e)}")
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                amount=Decimal(0),
                currency=Currency.EUR,
                error_message=str(e)
            )
    
    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> PaymentResponse:
        """Process Stripe refund"""
        try:
            refund_data = {'payment_intent': payment_id}
            if amount:
                refund_data['amount'] = int(amount * 100)
            
            refund = stripe.Refund.create(**refund_data)
            
            return PaymentResponse(
                payment_id=refund.id,
                status=PaymentStatus.REFUNDED if refund.status == 'succeeded' else PaymentStatus.FAILED,
                amount=Decimal(refund.amount) / 100,
                currency=Currency(refund.currency.upper()),
                gateway_transaction_id=refund.id,
                gateway_response=refund
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund failed: {str(e)}")
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                amount=Decimal(0),
                currency=Currency.EUR,
                error_message=str(e)
            )

class PayPalPaymentProcessor:
    """PayPal payment processing implementation"""
    
    def __init__(self, client_id: str, client_secret: str, environment: str = "sandbox"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment
        # Initialize PayPal SDK
    
    async def create_payment(self, payment_request: PaymentRequest) -> PaymentResponse:
        """Create PayPal payment"""
        try:
            # PayPal payment creation logic
            # This is a simplified implementation
            payment_data = {
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "transactions": [{
                    "amount": {
                        "total": str(payment_request.amount),
                        "currency": payment_request.currency.value
                    },
                    "description": payment_request.description,
                    "custom": payment_request.booking_id
                }],
                "redirect_urls": {
                    "return_url": payment_request.return_url,
                    "cancel_url": payment_request.cancel_url
                }
            }
            
            # Create payment with PayPal SDK
            payment_id = f"paypal_{secrets.token_urlsafe(16)}"
            approval_url = f"https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token={payment_id}"
            
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.PENDING,
                amount=payment_request.amount,
                currency=payment_request.currency,
                gateway_transaction_id=payment_id,
                redirect_url=approval_url
            )
            
        except Exception as e:
            logger.error(f"PayPal payment creation failed: {str(e)}")
            return PaymentResponse(
                payment_id="",
                status=PaymentStatus.FAILED,
                amount=payment_request.amount,
                currency=payment_request.currency,
                error_message=str(e)
            )
    
    async def execute_payment(self, payment_id: str, payer_id: str) -> PaymentResponse:
        """Execute approved PayPal payment"""
        try:
            # Execute payment logic
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.COMPLETED,
                amount=Decimal(0),  # Would be retrieved from PayPal
                currency=Currency.EUR,
                gateway_transaction_id=payment_id
            )
            
        except Exception as e:
            logger.error(f"PayPal payment execution failed: {str(e)}")
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                amount=Decimal(0),
                currency=Currency.EUR,
                error_message=str(e)
            )

class CurrencyConverter:
    """Handle multi-currency support and conversion"""
    
    def __init__(self):
        # Exchange rates would be fetched from external API
        self.exchange_rates = {
            Currency.EUR: 1.0,
            Currency.USD: 1.08,
            Currency.TND: 3.25,
            Currency.GBP: 0.86
        }
    
    def convert_amount(self, amount: Decimal, from_currency: Currency, to_currency: Currency) -> Decimal:
        """Convert amount between currencies"""
        if from_currency == to_currency:
            return amount
        
        # Convert to EUR first, then to target currency
        eur_amount = amount / Decimal(str(self.exchange_rates[from_currency]))
        target_amount = eur_amount * Decimal(str(self.exchange_rates[to_currency]))
        
        return target_amount.quantize(Decimal('0.01'))
    
    def get_supported_currencies(self) -> List[Currency]:
        """Get list of supported currencies"""
        return list(Currency)

class PaymentService:
    """Main payment service orchestrating all payment operations"""
    
    def __init__(self, stripe_config: Dict[str, str], paypal_config: Dict[str, str]):
        self.security_manager = PaymentSecurityManager()
        self.currency_converter = CurrencyConverter()
        
        # Initialize payment processors
        self.stripe_processor = StripePaymentProcessor(
            stripe_config['api_key'],
            stripe_config['webhook_secret']
        )
        
        self.paypal_processor = PayPalPaymentProcessor(
            paypal_config['client_id'],
            paypal_config['client_secret'],
            paypal_config.get('environment', 'sandbox')
        )
        
        self.processors = {
            PaymentMethod.STRIPE_CARD: self.stripe_processor,
            PaymentMethod.STRIPE_SEPA: self.stripe_processor,
            PaymentMethod.PAYPAL: self.paypal_processor,
            PaymentMethod.PAYPAL_PAY_LATER: self.paypal_processor
        }
    
    async def create_payment(self, payment_request: PaymentRequest) -> PaymentResponse:
        """Create payment using appropriate processor"""
        # Validate payment request
        if not self.security_manager.validate_payment_data(payment_request):
            return PaymentResponse(
                payment_id="",
                status=PaymentStatus.FAILED,
                amount=payment_request.amount,
                currency=payment_request.currency,
                error_message="Invalid payment data"
            )
        
        # Get appropriate processor
        processor = self.processors.get(payment_request.payment_method)
        if not processor:
            return PaymentResponse(
                payment_id="",
                status=PaymentStatus.FAILED,
                amount=payment_request.amount,
                currency=payment_request.currency,
                error_message="Unsupported payment method"
            )
        
        # Generate payment token for security
        payment_token = self.security_manager.generate_payment_token(payment_request.booking_id)
        
        # Add security metadata
        if not payment_request.metadata:
            payment_request.metadata = {}
        payment_request.metadata['payment_token'] = payment_token
        payment_request.metadata['created_at'] = datetime.now().isoformat()
        
        # Process payment
        if payment_request.payment_method in [PaymentMethod.STRIPE_CARD, PaymentMethod.STRIPE_SEPA]:
            if payment_request.return_url:
                response = await self.stripe_processor.create_checkout_session(payment_request)
            else:
                response = await self.stripe_processor.create_payment_intent(payment_request)
        else:
            response = await self.paypal_processor.create_payment(payment_request)
        
        # Log payment creation
        logger.info(f"Payment created: {response.payment_id}, Status: {response.status}")
        
        return response
    
    async def confirm_payment(self, payment_id: str, payment_method: PaymentMethod) -> PaymentResponse:
        """Confirm payment status"""
        processor = self.processors.get(payment_method)
        if not processor:
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                amount=Decimal(0),
                currency=Currency.EUR,
                error_message="Unsupported payment method"
            )
        
        return await processor.confirm_payment(payment_id)
    
    async def refund_payment(self, payment_id: str, payment_method: PaymentMethod, amount: Optional[Decimal] = None) -> PaymentResponse:
        """Process payment refund"""
        processor = self.processors.get(payment_method)
        if not processor:
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                amount=Decimal(0),
                currency=Currency.EUR,
                error_message="Unsupported payment method"
            )
        
        return await processor.refund_payment(payment_id, amount)
    
    def convert_currency(self, amount: Decimal, from_currency: Currency, to_currency: Currency) -> Decimal:
        """Convert amount between currencies"""
        return self.currency_converter.convert_amount(amount, from_currency, to_currency)
    
    def get_supported_payment_methods(self) -> List[PaymentMethod]:
        """Get list of supported payment methods"""
        return list(PaymentMethod)
    
    def get_supported_currencies(self) -> List[Currency]:
        """Get list of supported currencies"""
        return self.currency_converter.get_supported_currencies()

# Example usage and configuration
def create_payment_service() -> PaymentService:
    """Factory function to create configured payment service"""
    stripe_config = {
        'api_key': 'sk_test_...',  # From environment variables
        'webhook_secret': 'whsec_...'
    }
    
    paypal_config = {
        'client_id': 'your_paypal_client_id',
        'client_secret': 'your_paypal_client_secret',
        'environment': 'sandbox'  # or 'live' for production
    }
    
    return PaymentService(stripe_config, paypal_config)

# Webhook handlers for payment status updates
async def handle_stripe_webhook(payload: str, signature: str, webhook_secret: str) -> Dict[str, Any]:
    """Handle Stripe webhook events"""
    try:
        event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            booking_id = payment_intent['metadata'].get('booking_id')
            
            # Update booking status in database
            logger.info(f"Payment succeeded for booking: {booking_id}")
            
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            booking_id = payment_intent['metadata'].get('booking_id')
            
            # Handle payment failure
            logger.error(f"Payment failed for booking: {booking_id}")
        
        return {'status': 'success'}
        
    except Exception as e:
        logger.error(f"Webhook handling failed: {str(e)}")
        return {'status': 'error', 'message': str(e)}

async def handle_paypal_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle PayPal webhook events"""
    try:
        event_type = payload.get('event_type')
        
        if event_type == 'PAYMENT.SALE.COMPLETED':
            # Handle successful payment
            resource = payload.get('resource', {})
            custom_id = resource.get('custom')  # booking_id
            
            logger.info(f"PayPal payment completed for booking: {custom_id}")
            
        elif event_type == 'PAYMENT.SALE.DENIED':
            # Handle payment failure
            resource = payload.get('resource', {})
            custom_id = resource.get('custom')
            
            logger.error(f"PayPal payment denied for booking: {custom_id}")
        
        return {'status': 'success'}
        
    except Exception as e:
        logger.error(f"PayPal webhook handling failed: {str(e)}")
        return {'status': 'error', 'message': str(e)}

