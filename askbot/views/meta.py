"""
:synopsis: remaining "secondary" views for askbot

This module contains a collection of views displaying all sorts of secondary and mostly static content.
"""
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.template import RequestContext, Template
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.views import static
from django.views.decorators import csrf
from django.db.models import Max, Count
from askbot.forms import FeedbackForm
from askbot.utils.url_utils import get_login_url
from askbot.utils.forms import get_next_url
from askbot.mail import mail_moderators
from askbot.models import BadgeData, Award, User
from askbot.models import badges as badge_data
from askbot.skins.loaders import get_template, render_into_skin, render_text_into_skin
from askbot.conf import settings as askbot_settings
from askbot import skins

def generic_view(request, template = None, page_class = None):
    """this may be not necessary, since it is just a rewrite of render_into_skin"""
    if request is None:  # a plug for strange import errors in django startup
        return render_to_response('django_error.html')
    return render_into_skin(template, {'page_class': page_class}, request)

def config_variable(request, variable_name = None, mimetype = None):
    """Print value from the configuration settings
    as response content. All parameters are required.
    """
    #todo add http header-based caching here!!!
    output = getattr(askbot_settings, variable_name, '')
    return HttpResponse(output, mimetype = mimetype)

def about(request, template='about.html'):
    title = _('About %(site)s') % {'site': askbot_settings.APP_SHORT_NAME}
    data = {
        'title': title,
        'page_class': 'meta',
        'content': askbot_settings.FORUM_ABOUT
    }
    return render_into_skin('static_page.html', data, request)

def page_not_found(request, template='404.html'):
    return generic_view(request, template)

def server_error(request, template='500.html'):
    return generic_view(request, template)

def help(request):
    data = {
        'app_name': askbot_settings.APP_SHORT_NAME,
        'page_class': 'meta'
    }
    return render_into_skin('help.html', data, request)

def faq(request):
    if askbot_settings.FORUM_FAQ.strip() != '':
        data = {
            'title': _('FAQ'),
            'content': askbot_settings.FORUM_FAQ,
            'page_class': 'meta',
        }
        return render_into_skin(
            'static_page.html',
            data,
            request
        )
    else:
        data = {
            'gravatar_faq_url': reverse('faq') + '#gravatar',
            'ask_question_url': reverse('ask'),
            'page_class': 'meta',
        }
        return render_into_skin('faq_static.html', data, request)

@csrf.csrf_protect
def feedback(request):
    data = {'page_class': 'meta'}
    form = None

    if askbot_settings.ALLOW_ANONYMOUS_FEEDBACK is False:
        if request.user.is_anonymous():
            message = _('Please sign in or register to send your feedback')
            request.user.message_set.create(message=message)
            redirect_url = get_login_url() + '?next=' + request.path
            return HttpResponseRedirect(redirect_url)

    if request.method == "POST":
        form = FeedbackForm(
            is_auth=request.user.is_authenticated(),
            data=request.POST
        )
        if form.is_valid():
            if not request.user.is_authenticated():
                data['email'] = form.cleaned_data.get('email',None)
            data['message'] = form.cleaned_data['message']
            data['name'] = form.cleaned_data.get('name',None)
            template = get_template('email/feedback_email.txt', request)
            message = template.render(RequestContext(request, data))
            mail_moderators(_('Q&A forum feedback'), message)
            msg = _('Thanks for the feedback!')
            request.user.message_set.create(message=msg)
            return HttpResponseRedirect(get_next_url(request))
    else:
        form = FeedbackForm(is_auth = request.user.is_authenticated(),
                            initial={'next':get_next_url(request)})

    data['form'] = form
    return render_into_skin('feedback.html', data, request)
feedback.CANCEL_MESSAGE=_('We look forward to hearing your feedback! Please, give it next time :)')

def privacy(request):
    data = {
        'title': _('Privacy policy'),
        'page_class': 'meta',
        'content': askbot_settings.FORUM_PRIVACY
    }
    return render_into_skin('static_page.html', data, request)

def badges(request):#user status/reputation system
    #todo: supplement database data with the stuff from badges.py
    if askbot_settings.BADGES_MODE != 'public':
        raise Http404
    known_badges = badge_data.BADGES.keys()
    badges = BadgeData.objects.filter(slug__in = known_badges).order_by('slug')
    my_badges = []
    if request.user.is_authenticated():
        my_badges = Award.objects.filter(
                                user=request.user
                            ).values(
                                'badge_id'
                            ).distinct()
        #my_badges.query.group_by = ['badge_id']

    data = {
        'active_tab': 'badges',
        'badges' : badges,
        'page_class': 'meta',
        'mybadges' : my_badges,
        'feedback_faq_url' : reverse('feedback'),
    }
    return render_into_skin('badges.html', data, request)

def badge(request, id):
    #todo: supplement database data with the stuff from badges.py
    badge = get_object_or_404(BadgeData, id=id)

    badge_recipients = User.objects.filter(
                            award_user__badge = badge
                        ).annotate(
                            last_awarded_at = Max('award_user__awarded_at'),
                            award_count = Count('award_user')
                        ).order_by(
                            '-last_awarded_at'
                        )

    data = {
        'active_tab': 'badges',
        'badge_recipients' : badge_recipients,
        'badge' : badge,
        'page_class': 'meta',
    }
    return render_into_skin('badge.html', data, request)
