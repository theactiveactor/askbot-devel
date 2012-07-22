"""Custom django signals defined for the askbot forum application.
"""
import django.dispatch
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete, post_syncdb
try:
    from django.db.models.signals import m2m_changed
except ImportError:
    pass

tags_updated = django.dispatch.Signal(
                        providing_args=['tags', 'user', 'timestamp']
                    )

#todo: this one seems to be unused
edit_question_or_answer = django.dispatch.Signal(
                                    providing_args=['instance', 'modified_by']
                                )
delete_question_or_answer = django.dispatch.Signal(
                                    providing_args=['instance', 'deleted_by']
                                )
flag_offensive = django.dispatch.Signal(providing_args=['instance', 'mark_by'])
remove_flag_offensive = django.dispatch.Signal(providing_args=['instance', 'mark_by'])
user_updated = django.dispatch.Signal(providing_args=['instance', 'updated_by'])
user_registered = django.dispatch.Signal(providing_args=['user',])
#todo: move this to authentication app
user_logged_in = django.dispatch.Signal(providing_args=['session'])

post_updated = django.dispatch.Signal(
                                providing_args=[
                                            'post',
                                            'updated_by',
                                            'newly_mentioned_users'
                                        ]
                            )
post_revision_published = django.dispatch.Signal(
                                providing_args = [
                                    'revision',
                                    'was_approved'
                                ]
                            )
site_visited = django.dispatch.Signal(providing_args=['user', 'timestamp'])

def pop_signal_receivers(signal):
    """disables a given signal by removing listener functions
    and returns the list
    """
    receivers = signal.receivers
    signal.receivers = list()
    return receivers

def set_signal_receivers(signal, receiver_list):
    """assigns a value of the receiver_list
    to the signal receivers
    """
    signal.receivers = receiver_list

def pop_all_db_signal_receivers():
    """loops through all relevant signals
    pops their receivers and returns a
    dictionary where signals are keys
    and lists of receivers are values
    """
    #this is the only askbot signal that is not defined here
    #must use this to avoid a circular import
    from askbot.models.badges import award_badges_signal
    signals = (
        #askbot signals
        tags_updated,
        edit_question_or_answer,
        delete_question_or_answer,
        flag_offensive,
        remove_flag_offensive,
        user_updated,
        user_logged_in,
        user_registered,
        post_updated,
        award_badges_signal,
        #django signals
        pre_save,
        post_save,
        pre_delete,
        post_delete,
        post_syncdb,
    )
    if 'm2m_changed' in globals():
        signals += (m2m_changed, )

    receiver_data = dict()
    for signal in signals:
        receiver_data[signal] = pop_signal_receivers(signal)

    return receiver_data

def set_all_db_signal_receivers(receiver_data):
    """takes receiver data as an argument
    where the argument is as returned by the
    pop_all_db_signal_receivers() call
    and sets the receivers back to the signals
    """
    for (signal, receivers) in receiver_data.items():
        signal.receivers = receivers

# Classes and signal for collecting search results from third party apps.
class AskbotSearchGroup(object):
    # TODO: Support more results link
    def __init__(self, name, priority, results = None):
        self.name = name
        self.priority = priority
        self.results = results
        
        if not self.results:
            self.results = []
    
    def addSearchResult(self, result):
        self.results.append(result)

    def __str__(self):
        return "name=%s priority=%s results=%i" % (self.name, self.priority, len(self.results))

class AskbotSearchResult(object):
    # TODO: Support illustration photos.
    def __init__(self, title, url, description):
        self.title = title
        self.url = url
        self.description = description
        
'''
Each receiver may return 1 group. Groups will be merged by priority (1-10). 
Higher number means the group will show up first.
Groups with same priorities will be merged by alphabetical order.
Questions results (askbot default) will always show up last.
'''
search_askbot_signal = django.dispatch.Signal(providing_args=["query"])