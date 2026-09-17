import random

from config.constants import EnvironmentChoices
from django import template
from django.conf import settings

register = template.Library()

# Keep title/description paired so a render never mixes halves of two jokes.
JOKE_REGISTRY = [
    {
        "title": "Stale navigation, again",
        "description": (
            "The URL knows best, the sidebar disagrees. Last fix updated "
            "#main-content and apparently called it a day."
        ),
    },
    {
        "title": "Page 500s after login, also navbar is haunted",
        "description": (
            "Steps to reproduce: navigate anywhere.\nExpected: the whole "
            "page agrees on where I am.\nActual: #main-content is "
            "enlightened, everything else is still buffering circa the "
            "last full page load."
        ),
    },
    {
        "title": "The URL has been overruled",
        "description": (
            "The address bar says Project 2. The active sidebar item says "
            "Project 1. Breadcrumbs have declined to comment. Please "
            "restore democratic control to the URL."
        ),
    },
    {
        "title": "One target was not enough",
        "description": (
            "Updated #main-content successfully. Unfortunately, the "
            "sidebar also contains state. The breadcrumbs would like to "
            "have a word."
        ),
    },
    {
        "title": "It works after a hard refresh",
        "description": (
            "Everything looks correct after refreshing the entire page. "
            "Unfortunately, that rather defeats the purpose of using HTMX."
        ),
    },
    {
        "title": "The partial is innocent",
        "description": (
            "The requested fragment is rendering correctly. Investigation "
            "has moved to the suspicious collection of stale UI "
            "surrounding it. This is why we can't have nice partials."
        ),
    },
    {
        "title": "OOB swap request denied",
        "description": (
            "Filed a formal request for the sidebar to be swapped "
            "out-of-band along with everything else. Request still "
            "pending review from whoever wrote the original view."
        ),
    },
]


@register.simple_tag
def random_ticket_joke():
    """Return a random {title, description} pair for wizard placeholder defaults."""
    if settings.ENVIRONMENT == EnvironmentChoices.BENCH:
        return JOKE_REGISTRY[0]
    return random.choice(JOKE_REGISTRY)
