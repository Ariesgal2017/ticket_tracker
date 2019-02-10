from django.conf.urls import url

from .views import *

urlpatterns = [

    url(r'^(?P<pk>\d+)/$',
        view=TicketDetailView.as_view(),
        name="ticket_detail"),

    url(regex=r"^new/$",
        view=TicketUpdateView,
        name="new_ticket"),

    url(r'^update/(?P<pk>\d+)/$',
        view=TicketUpdateView,
        name="update_ticket"),

    url(r'^upvote/(?P<pk>\d+)/$',
        view=upvote_ticket,
        name='upvote_ticket'),

    url(r'^close/(?P<pk>\d+)/$',
        view=TicketCommentView, kwargs={'action': 'closed'},
        name='close_ticket'),

    url(r'^reopen/(?P<pk>\d+)/$',
        view=TicketCommentView, kwargs={'action': 'reopened'},
        name='reopen_ticket'),

    url(r'^accept/(?P<pk>\d+)/$',
        view=TicketCommentView, kwargs={'action': 'accept'},
        name='accept_ticket'),

    url(r'^assign/(?P<pk>\d+)/$',
        view=TicketCommentView, kwargs={'action': 'assign'},
        name='assign_ticket'),

    url(r'^comment/(?P<pk>\d+)/$',
        view=TicketCommentView, kwargs={'action': 'comment'},
        name='comment_ticket'),

    url(r'^split/(?P<pk>\d+)/$',
        view=SplitTicketView,
        name="split_ticket"),

    # ===========
    # Ticket Lists
    url(regex=r"^$",
        view=TicketListView.as_view(),
        name="ticket_list"),

    url(regex=r"^mytickets/(?P<username>[\w.@+-]+)/$",
        view=TicketListView.as_view(),
        name="my_ticket_list"),

    url(regex=r"^assinged_to/(?P<username>[\w.@+-]+)/$",
        view=TicketListView.as_view(),
        name="assigned_to", kwargs={'what': 'assigned_to'}),

    url(regex=r"^submitted_by/(?P<username>[\w.@+-]+)/$",
        view=TicketListView.as_view(),
        name="submitted_by", kwargs={'what': 'submitted_by'}),

    url(regex=r"^open/$",
        view=OpenTicketListView.as_view(),
        name="open_tickets"),

    url(regex=r"^closed/$",
        view=ClosedTicketListView.as_view(),
        name="closed_tickets"),

    url(regex=r"^bugreports/$",
        view=BugTicketListView.as_view(),
        name="bug_reports"),

    url(regex=r"^featurerequests/$",
        view=FeatureTicketListView.as_view(),
        name="feature_requests"),

        #project tags
    #path('tag/<slug:slug>', TagIndexView.as_view(),
    #     name='tagged'),


    url(regex=r"^tagged/(?P<slug>[-\w]+)/$",
        view=TagIndexView.as_view(),
        name="tickets_tagged_with"),



]
