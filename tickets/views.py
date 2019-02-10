from collections import OrderedDict

from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic.list import ListView
from django.views.generic import DetailView

from taggit.models import Tag

from .models import Ticket, UserVoteLog, FollowUp
from .forms import (TicketForm, CloseTicketForm, SplitTicketForm,
                    # CommentForm,
                    AcceptTicketForm, AssignTicketForm, CommentTicketForm)
from .utils import is_admin




class TagMixin(object):

    def get_context_data(self, **kwargs):
        context = super(TagMixin, self).get_context_data(**kwargs)
        tag_slug = self.kwargs.get('slug')
        context['tag'] = Tag.objects.filter(slug=tag_slug).first()
        context['tags'] = Tag.objects.all()
        return context


class TagIndexView(TagMixin, ListView):
    template_name = 'tickets/ticket_list.html'
    model = Ticket
    paginate_by =  50#RECORDS_PER_PAGE

    def get_queryset(self):
        return Ticket.objects.filter(tags__slug=self.kwargs.get('slug'))



class TicketDetailView(DetailView):
    '''
    A view to render details of a single ticket.

    **Context:**

    ``object``
        a :model:`ticket.Ticket` object.

    ``comments``
        a list of :model:`tickets.FollowUp` objects associated with this
        ticket.

    **Template:**

    :template:`/tickets/ticket_detail.html`

    '''
    model = Ticket

    def get_context_data(self, **kwargs):
        '''Get the comments associated with this ticket.  Only include
        the public comments unless  request.user is an admin or
        created the ticket
        '''

        context = super(TicketDetailView, self).get_context_data(**kwargs)
        user = self.request.user
        pk = context['ticket'].id
        ticket = Ticket.objects.get(id=pk)
        if is_admin(user) or user == ticket.submitted_by:
            comments = FollowUp.all_comments.filter(
                ticket__pk=pk).order_by('-created_on')
        else:
            comments = FollowUp.objects.filter(
                ticket__pk=pk).order_by('-created_on')
        context['comments'] = comments
        return context


class TicketListViewBase(TagMixin, ListView):
    '''A base class for all ticket listviews.'''
    model = Ticket

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        context['filters'] = get_ticket_filters()
        return context


def get_ticket_filters():
    """Return a dictionary that will be used to create the dynamic filters
    on the fitler lists.  There will be one element for each filter
    (status, application, ticket type, priority, submitted by, and
    assigned to.

    """

    values = Ticket.TICKET_STATUS_CHOICES
    status = [x[0] for x in values]

    values = sorted(Ticket.TICKET_PRIORITY_CHOICES,
                    key=lambda x: x[0])
    priority = [x[1] for x in values]

    values = Ticket.TICKET_TYPE_CHOICES
    ticket_types = [x[1] for x in values]

    values = Ticket.objects.all().values_list('application__application')\
                                 .distinct()
    applications = [x[0] for x in values]

    values = Ticket.objects.all().values_list('submitted_by__username')\
                                 .distinct()
    submitted_by = [x[0] for x in values]

    values = Ticket.objects.all().values_list('assigned_to__username')\
                                 .distinct()
    assigned_to = [x[0] for x in values]

    ticket_filters = OrderedDict()

    ticket_filters['status'] = status
    ticket_filters['application'] = applications
    ticket_filters['priority'] = priority
    ticket_filters['type'] = ticket_types
    ticket_filters['submitted_by'] = submitted_by
    ticket_filters['assigned_to'] = assigned_to

    return ticket_filters


class TicketListView(TicketListViewBase):
    '''A view to render a list of tickets. If a query string and/or a
    user is provided, they will be used to filter the queryset,
    otherwise all tickets are returned in reverse chronological
    order.

    **Context:**

    ``object_list``
        a list of :model:`ticket.Ticket` objects.

    ``query``
        the query search string used to filter tickets. submitted via
        the quick seach bar.

``user``

    **Template:**

    :template:`/tickets/ticket_list.html`

    '''

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        userid = self.kwargs.get('userid', None)
        if userid:
            try:
                context['user'] = User.objects.get(id=userid)
            except User.DoesNotExist:
                user = None

        context['query'] = self.request.GET.get("q")

        what = self.kwargs.get('what', None)
        if what:
            context['what'] = what.replace('_', ' ')

        return context


    def get_queryset(self):
        q = self.request.GET.get("q")
        userid = self.kwargs.get('userid', None)
        what = self.kwargs.get('what', None)

        tickets = Ticket.objects.order_by("-created_on")\
                                .prefetch_related('application',
                                                  'submitted_by',
                                                  'assigned_to')

        try:
            user = User.objects.get(id=userid)
        except User.DoesNotExist:
            user = None

        if q:
            tickets = tickets.filter(description__icontains=q)

        if user:
            if what == 'submitted_by':
                return tickets.filter(submitted_by=user)
            elif what == 'assigned_to':
                return tickets.filter(assigned_to=user)
            else:
                return tickets.filter(Q(submitted_by=user) |
                                      Q(assigned_to=user))
        else:
            # No q or user is specified so we return the full queryset
            return tickets.all()


class ClosedTicketListView(TicketListViewBase):
    '''A list of only closed tickets.

    **Context:**

    ``object_list``
        a list of :model:`ticket.Ticket` objects where
        status is either 'closed', 'duplicate' or 'split'.

    **Template:**

    :template:`/tickets/ticket_list.html`

    '''

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        context['closed'] = True
        return context

    def get_queryset(self):
        inactive_codes = ['closed', 'split', 'duplicate']
        return Ticket.objects.filter(
            status__in=inactive_codes).order_by("-created_on")


class OpenTicketListView(TicketListViewBase):

    '''A list of only open tickets.

    **Context:**

    ``object_list``
        a list of :model:`ticket.Ticket` objects where
        status is either 'new','accepted', 'assigned' or 'reopened'

    **Template:**

    :template:`/tickets/ticket_list.html`

    '''

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        context['open'] = True
        return context

    def get_queryset(self):
        open_codes = ['new', 'accepted', 'assigned', 'reopened']
        return Ticket.objects.filter(
            status__in=open_codes).order_by("-created_on")


class BugTicketListView(TicketListViewBase):
    '''
    A list of only bug reports tickets.

    **Context:**

    ``object_list``
        a list of :model:`ticket.Ticket` objects where
        ticket_type=='bug'

    **Template:**

    :template:`/tickets/ticket_list.html`

    '''

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        filters = get_ticket_filters()
        filters.pop('type')
        context['filters'] = filters
        context['type'] = 'Bug Reports'
        return context

    def get_queryset(self):
        return Ticket.objects.filter(
            ticket_type='bug').order_by("-created_on")


class FeatureTicketListView(TicketListViewBase):
    '''
    A list of only feature request tickets.

    **Context:**

    ``object_list``
        a list of :model:`ticket.Ticket` objects where
        ticket_type=='feature'

    **Template:**

    :template:`/tickets/ticket_list.html`

    '''

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        filters = get_ticket_filters()
        filters.pop('type')
        context['filters'] = filters
        context['type'] = 'Feature Requests'
        return context

    def get_queryset(self):
        return Ticket.objects.filter(
            ticket_type='feature').order_by("-created_on")


@login_required
def TicketUpdateView(request, pk=None,
                     template_name='tickets/ticket_form.html'):
    '''
    A view to allow users to update existing tickets or create new
    ones.

    New tickets can be created by any logged in user, but only
    administrators or the tickets original submitter can make changes to
    an existing ticket.

    If a primary key is include in the request, an attempt will be
    made to retrieve the associated ticket. If no primary key is
    included, a new ticket will be created.

    **Context:**

    ``form``
        an instance of a TicketForm

    **Template:**

    :template:`/tickets/ticket_form.html`

    '''

    if pk:
        ticket = get_object_or_404(Ticket, pk=pk)
        if not (request.user == ticket.submitted_by or
                is_admin(request.user)):
            return HttpResponseRedirect(ticket.get_absolute_url())
    else:
        ticket = Ticket(submitted_by=request.user, status='new')

    if request.POST:
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            new_ticket = form.save()
            return HttpResponseRedirect(new_ticket.get_absolute_url())
    else:
        form = TicketForm(instance=ticket)

    return render(request, template_name, {'form': form})


@login_required
def SplitTicketView(request, pk=None,
                    template_name='tickets/split_ticket_form.html'):
    '''
    If a ticket is too complex to handle as a single issue, this
    view allows administrators to split the ticket into two child
    tickets.  The original ticket is closed, but is referenced by the
    children.  By default, all of the fields in the child ticket are
    initially set to the values for the same field in the parent.

    **Context:**

    ``form``
        an instance of a SplitTicketForm

    **Template:**

    :template:`/tickets/split_ticket_form.html`

    '''

    # ticket = get_object_or_404(Ticket, pk=pk)

    try:
        ticket = Ticket.objects.get(id=pk)
    except Ticket.DoesNotExist:
        url = reverse('ticket_list')
        return HttpResponseRedirect(url)

    if is_admin(request.user) is False:
        return HttpResponseRedirect(ticket.get_absolute_url())

    # start with the same data in both tickets as the original.
    initial = {
        'status1': 'new',
        'ticket_type1': ticket.ticket_type,
        'priority1': ticket.priority,
        'application1': ticket.application,
        'assigned_to1': ticket.assigned_to,
        'description1': ticket.description,
        'status2': 'new',
        'ticket_type2': ticket.ticket_type,
        'priority2': ticket.priority,
        'application2': ticket.application,
        'assigned_to2': ticket.assigned_to,
        'description2': ticket.description}

    if request.method == 'POST':
        form = SplitTicketForm(data=request.POST, user=request.user,
                               original_ticket=ticket)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(ticket.get_absolute_url())
    else:
        form = SplitTicketForm(initial=initial,
                               user=request.user, original_ticket=ticket)

    return render(request, template_name, {'form': form})


##@login_required
##def TicketFollowUpView(request, pk, action='closed',
##                       template_name='tickets/comment_form.html'):
##
##    '''This view is used by administrators to accept, assign, close and
##    re-open tickets.  Tickets can be closed outright or as a
##    duplicate.  In all cases a comment (explanation) is required.
##
##   **Context:**
##
##    ``ticket``
##        a :model:`ticket.Ticket` object.
##
##    ``form``
##        an instance of a CloseTicketForm
##
##    **Template:**
##
##    :template:`/tickets/comment_form.html`
##
##    '''
##
##    try:
##        ticket = Ticket.objects.get(pk=pk)
##    except Ticket.DoesNotExist:
##        url = reverse('ticket_list')
##        return HttpResponseRedirect(url)
##
##    if not is_admin(request.user):
##        return redirect(ticket.get_absolute_url())
##
##    if request.POST:
##        form = CloseTicketForm(request.POST, ticket=ticket,
##                               user=request.user, action=action)
##        if form.is_valid():
##            form.save()
##            return HttpResponseRedirect(ticket.get_absolute_url())
##        else:
##            render(request, template_name, {'form': form, 'ticket': ticket})
##
##    else:
##        form = CloseTicketForm(ticket=ticket, user=request.user,
##                           action=action)
##
##    return render(request, template_name, {'form': form, 'ticket': ticket})
##

#==============================
@login_required
def TicketCommentView(request, pk, action='comment'):

    '''
    Add a comment to a ticket. If the user is an administrator,
    this view is also used to close and re-open tickets.
    (i.e. create a new :model:FollowUp
    object).  No actions are associated with the new FollowUp object.

   **Context:**

    ``ticket``
        a :model:`ticket.Ticket` object.

    ``form``
        an instance of a CommentForm

    **Template:**
            template = 'tickets/close_repopen_ticket_form.html'
    :template:`/tickets/comment_form.html`

    '''

    try:
        ticket = Ticket.objects.get(pk=pk)
    except Ticket.DoesNotExist:
        url = reverse('ticket_list')
        return HttpResponseRedirect(url)

    if not is_admin(request.user) and action != 'comment':
        return redirect(ticket.get_absolute_url())

    if action in ('closed', 'reopened'):
        template = 'tickets/close_reopen_ticket_form.html'
    else:
        template = 'tickets/comment_form.html'

    if request.POST:
        if action in ('closed', 'reopened'):
            form = CloseTicketForm(request.POST, ticket=ticket,
                                   user=request.user,
                                   action=action)
        elif action == 'comment':
            form = CommentTicketForm(request.POST, ticket=ticket,
                                     user=request.user)
        elif action == 'accept':
            form = AcceptTicketForm(request.POST, ticket=ticket,
                                    user=request.user)
        else:
            # i.e. action==assign
            form = AssignTicketForm(request.POST, ticket=ticket,
                                    user=request.user)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(ticket.get_absolute_url())
        else:
            render(request,
                   template,
                   {'form': form, 'ticket': ticket, 'action': action})
    else:
        if action in ('closed', 'reopened'):
            form = CloseTicketForm(ticket=ticket,
                                   user=request.user,
                                   action=action)
        elif action == 'comment':
            form = CommentTicketForm(ticket=ticket, user=request.user)
        elif action == 'accept':
            form = AcceptTicketForm(ticket=ticket, user=request.user)
        else:
            if ticket.assigned_to and action == 'assign':
                action = 're-assign'
            form = AssignTicketForm(ticket=ticket, user=request.user)

    return render(request,
                  template,
                  {'form': form, 'ticket': ticket, 'action': action})


@login_required
def upvote_ticket(request, pk):
    '''
    A view to increment the vote count for a ticket.  Only allow
    votes if user has logged in and then only if they have not voted
    for this ticket yet.'

    No template is rendered in this view.  The user is immediately
    re-directed back to the detail view for the ticket in question.

    '''
    ticket = Ticket.objects.get(pk=pk)
    try:
        user = User.objects.get(id=request.user.id)
    except User.DoesNotExist:
        user = None

    if user:
        p, created = UserVoteLog.objects.get_or_create(ticket=ticket,
                                                       user=user)
        if ticket and created:
            ticket.up_vote()
    return HttpResponseRedirect(ticket.get_absolute_url())
