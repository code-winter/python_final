from django.core.mail import send_mail
from celery import shared_task


@shared_task()
def send_token_email(email, token):
    send_mail(
        subject="Your New Token",
        message=f"\tNew token: {token}\n\nThank you!",
        recipient_list=[email],
        from_email=None,
        fail_silently=False,
    )
    return 'email sent'
