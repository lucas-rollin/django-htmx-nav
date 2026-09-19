from django.contrib import messages
from django.shortcuts import get_object_or_404
from htmx_nav import Swap, has_messages, render_nav


def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.delete()
    messages.success(request, f"Ticket #{ticket_id} deleted.")

    # No navigation involved, just OOB updates alongside the response
    return render_nav(
        request,
        "tickets/empty_state.html",
        partial=None,
        swaps=[
            Swap.delete(f"ticket-row-{ticket_id}"),
            Swap.text("open-tickets-count", str(Ticket.objects.filter(status="open").count())),
            Swap("components/_messages.html", target_id="messages", include_if=has_messages),
        ],
    )