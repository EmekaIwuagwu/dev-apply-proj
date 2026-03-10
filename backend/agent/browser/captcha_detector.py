import re
import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)

# Known CAPTCHA signals in page source and DOM
CAPTCHA_SIGNALS = [
    "recaptcha",
    "hcaptcha",
    "cf-turnstile",
    "arkose",
    "geetest",
    "data-sitekey",
    "captcha-container",
    "challenge-form",
    "cf-challenge",
    "verify you are human",
    "prove you're not a robot",
    "complete the security check",
    "one-time password",
    "enter the code we sent",
    "verification code",
    "sms verification",
    "check your email for a code",
]

OTP_SIGNALS = [
    "one-time password",
    "otp",
    "verification code",
    "enter the code",
    "sent to your email",
    "sent to your phone",
    "check your inbox",
    "resend code",
]

async def page_has_captcha(page: Page) -> bool:
    """
    Scans the page DOM and visible text for CAPTCHA or OTP signals.
    Returns True if any challenge is detected.
    """
    try:
        page_content = await page.content()
        lower_content = page_content.lower()

        # Check for visible text signals
        for signal in CAPTCHA_SIGNALS + OTP_SIGNALS:
            if signal in lower_content:
                logger.warning(f"CAPTCHA/OTP signal detected: {signal}")
                return True

        # Check for iframes from known CAPTCHA providers
        captcha_frames = await page.query_selector_all(
            'iframe[src*="recaptcha"], iframe[src*="hcaptcha"], '
            'iframe[src*="challenges.cloudflare.com"], iframe[src*="arkoselabs"]'
        )
        if captcha_frames:
            logger.warning("CAPTCHA iframe detected")
            return True

    except Exception as e:
        logger.error(f"Error checking for CAPTCHA: {str(e)}")
        # If we can't read the page reliably, assume it might be a bot wall
        return True 

    return False

async def url_is_blocked(url: str) -> bool:
    """
    Checks if the URL belongs to an explicitly blocked portal.
    """
    # Import inside to avoid circular deps if portal_config grows
    from agent.utils.portal_config import BLOCKED_PORTALS
    for portal in BLOCKED_PORTALS:
        if portal["base_url"] in url:
            logger.info(f"URL {url} is on blocked portal list: {portal['name']}")
            return True
    return False
