from django.contrib import messages
from htmx_nav import Swap, render_with_swaps, has_messages


def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.delete()
    messages.success(request, f"Ticket #{ticket_id} deleted.")

    # No navigation involved, just OOB updates alongside the response
    return render_with_swaps(
        request,
        "tickets/empty_state.html",
        swaps=[
            # Remove the row (hx-swap-oob="delete")
            Swap.delete(f"ticket-row-{ticket_id}"),
            # Raw text swap skips the template engine
            Swap.text("open-tickets-count", str(Ticket.objects.filter(status="open").count())),
            # Only render messages partial if any are queued
            Swap("components/_messages.html", target_id="messages", include_if=has_messages),
        ],
    )