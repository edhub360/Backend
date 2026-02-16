import stripe
from typing import Optional, List, Dict
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class StripeClient:
    @staticmethod
    def create_customer(user_id: str, email: Optional[str] = None) -> str:
        """Create Stripe customer with metadata"""
        customer_data = {
            "metadata": {"user_id": user_id}
        }
        if email:
            customer_data["email"] = email
            
        customer = stripe.Customer.create(**customer_data)
        return customer.id

    @staticmethod
    def create_checkout_session(
        customer_id: str, 
        price_id: str, 
        success_url: str, 
        cancel_url: str,
        metadata: dict = None,  # ADD THIS
        mode: str = "subscription"
    ) -> str:
        """Create Stripe Checkout session"""
        
        params = {
            "customer": customer_id,
            "mode": mode,
            "payment_method_types": ["card"],
            "line_items": [{
                "price": price_id, 
                "quantity": 1
            }],
            "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": cancel_url,
        }
        
        # ADD METADATA IF PROVIDED
        if metadata:
            params["metadata"] = metadata
        
        session = stripe.checkout.Session.create(**params)
        return session.url


    @staticmethod
    def cancel_subscription(sub_id: str, cancel_at_period_end: bool = True) -> None:
        """Cancel subscription"""
        stripe.Subscription.modify(
            sub_id,
            cancel_at_period_end=cancel_at_period_end
        )

    @staticmethod
    def retrieve_subscription(sub_id: str):
        """Get full subscription details"""
        return stripe.Subscription.retrieve(sub_id)

    @staticmethod
    def get_webhook_event(payload: bytes, sig_header: str, webhook_secret: str):
        """Verify and parse webhook"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            return event
        except ValueError:
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise Exception("Invalid signature")

    @staticmethod
    def parse_checkout_session(session: dict):
        """Extract data from checkout.session.completed"""
        return {
            "customer_id": session.get("customer"),
            "subscription_id": session.get("subscription"),
            "user_id": session["metadata"].get("user_id"),
            "payment_status": session.get("payment_status")
        }
    
    @staticmethod
    def get_payment_methods(stripe_customer_id: str) -> List[Dict]:
        """Get all payment methods for a customer"""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=stripe_customer_id,
                type="card"
            )
            
            # Get customer's default payment method
            customer = stripe.Customer.retrieve(stripe_customer_id)
            default_pm_id = customer.invoice_settings.default_payment_method
            
            return [
                {
                    "id": pm.id,
                    "brand": pm.card.brand,
                    "last4": pm.card.last4,
                    "exp_month": pm.card.exp_month,
                    "exp_year": pm.card.exp_year,
                    "is_default": pm.id == default_pm_id
                }
                for pm in payment_methods.data
            ]
        except Exception as e:
            print(f"❌ Stripe payment method fetch error: {str(e)}")
            return []
        
    @staticmethod
    def create_customer_portal_session(customer_id: str, return_url: str) -> str:
        """Create Stripe Customer Portal session"""
        try:
            print(f"🔗 Creating portal with return URL: {return_url}")
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            print(f"✅ Portal session created: {session.url}")
            return session.url
        except Exception as e:
            print(f"❌ Stripe portal error: {str(e)}")
            raise

