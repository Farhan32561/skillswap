# Pranay's part
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from ankon.skills.models import SkillOffer, SkillWanted
from .models import Review
from .forms import ExchangeRequestForm, ReviewForm
from .services import find_matches, send_request, transition, write_review, for_participant, present_exchange

@login_required
def dashboard(request):
    matches = find_matches(request.user)
    exchanges = for_participant(request.user)
    return render(request, 'exchanges/dashboard.html', {
        'stats': {'active_skills': SkillOffer.objects.filter(user=request.user).count() + SkillWanted.objects.filter(user=request.user).count(),
                  'pending_requests': exchanges.filter(receiver=request.user, status='pending').count(),
                  'matches': len(matches), 'completed_exchanges': exchanges.filter(status='completed').count()},
        'recommended_matches': matches[:4],
        'recent_requests': [present_exchange(item, request.user) for item in exchanges[:5]],
    })

@login_required
def matches(request):
    page = Paginator(find_matches(request.user), 12).get_page(request.GET.get('page'))
    return render(request, 'exchanges/matches.html', {'matches': page.object_list, 'page_obj': page})

@login_required
@require_http_methods(['GET', 'POST'])
def send_exchange_request(request, pk):
    receiver = get_object_or_404(get_user_model(), pk=pk, is_active=True)
    if receiver.pk == request.user.pk:
        messages.error(request, 'You cannot request an exchange with yourself.')
        return redirect('matches')
    # Existing cards post without a selection: show the selection step first.
    submitting = request.method == 'POST' and 'sender_skill' in request.POST
    form = ExchangeRequestForm(request.POST if submitting else None, sender=request.user, receiver=receiver)
    if submitting and form.is_valid():
        try:
            exchange = send_request(request.user, receiver, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error.messages)
        else:
            messages.success(request, 'Exchange request sent.')
            return redirect('exchange_detail', pk=exchange.pk)
    return render(request, 'exchanges/send_request.html', {'form': form, 'partner': receiver})

@login_required
def exchange_requests(request):
    exchanges = for_participant(request.user)
    return render(request, 'exchanges/exchange_requests.html', {
        'received_requests': [present_exchange(x, request.user) for x in exchanges.filter(receiver=request.user)],
        'sent_requests': [present_exchange(x, request.user) for x in exchanges.filter(sender=request.user)],
    })

@login_required
def exchange_detail(request, pk):
    exchange = get_object_or_404(for_participant(request.user), pk=pk)
    return render(request, 'exchanges/exchange_detail.html', {'exchange': present_exchange(exchange, request.user)})

@login_required
@require_POST
def respond_exchange(request, pk, action=None):
    exchange = get_object_or_404(for_participant(request.user), pk=pk)
    action = action or request.POST.get('decision')
    if action not in ('accept', 'reject', 'cancel', 'complete'):
        raise PermissionDenied('Invalid action.')
    try:
        status = transition(exchange, request.user, action)
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    else:
        messages.success(request, f'Exchange {status}.')
    return redirect('exchange_detail', pk=pk)

@login_required
def exchange_history(request):
    page = Paginator(for_participant(request.user).filter(status='completed'), 12).get_page(request.GET.get('page'))
    return render(request, 'exchanges/exchange_history.html', {
        'completed_exchanges': [present_exchange(item, request.user) for item in page], 'page_obj': page,
    })

@login_required
@require_http_methods(['GET', 'POST'])
def review(request, pk):
    exchange = get_object_or_404(for_participant(request.user), pk=pk)
    if exchange.status != 'completed':
        messages.error(request, 'Complete the exchange before leaving a review.')
        return redirect('exchange_detail', pk=pk)
    existing = Review.objects.filter(exchange=exchange, reviewer=request.user).first()
    form = ReviewForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and existing:
        messages.info(request, 'You have already reviewed this exchange.')
        return redirect('review', pk=pk)
    if request.method == 'POST' and form.is_valid():
        try:
            write_review(exchange, request.user, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error.messages)
        else:
            messages.success(request, 'Thank you for sharing your experience.')
            return redirect('review', pk=pk)
    return render(request, 'exchanges/review.html', {'exchange': present_exchange(exchange, request.user), 'form': form, 'review': existing})
