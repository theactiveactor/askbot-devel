'''
Implements django-articles integration.
Requires django-articles to be added as an installed app.
'''


from articles.models import Article, Tag
from askbot.models.signals import AskbotSearchGroup, AskbotSearchResult, \
    search_askbot_signal
from askbot.skins.loaders import render_into_skin
from askbot.utils import functions
from django.core.urlresolvers import reverse
from django.db.models.query_utils import Q
from django.http import Http404
from django.template.context import RequestContext
import logging
import random

def getArticleUrl(article):
    return reverse("articledirView", kwargs={"slug" : article.slug})

def getBasicArticleDisplay(article):
    '''
    Return basic display dict for an article entry.
    '''
    outDict = {}
    
    outDict["title"] = article.title
    outDict["url"] = getArticleUrl(article)
    outDict["teaser"] = article.teaser
    
    return outDict

def getBasicTagDisplay(tag, isActive=False):
    '''
    Return basic display dict for a tag.
    '''
    outDict = {}
    outDict["name"] = tag.name
    outDict["url"] = reverse("articledirTag", kwargs={"slug" : tag.slug})
    outDict["description"] = tag.description
    outDict["is_active"] = isActive
    
    return outDict

def getRelatedArticles(currentArticle, num=5):
    '''
    Get related articles for a specified article.
    '''
    # Find all articles which matches a tag.
    q = Q()
    for tag in currentArticle.tags.all():
        q |= Q(tags=tag)
    
    allRelatedArticles = list(Article.objects.filter(q).distinct().order_by("publish_date").exclude(id=currentArticle.id))
    
    # Shuffle article display in a predictable ways.
    random.seed(currentArticle.id)
    random.shuffle(allRelatedArticles)
    
    return allRelatedArticles[:num]

def requestView(request, **kwargs):
    '''
    Display a single article (identified by slug).
    '''
    context = {}
    
    # Fetch current article.
    try:
        currentArticle = Article.objects.get(slug=kwargs["slug"])
    except Tag.DoesNotExist,e:
        logging.error("Article with slug does not exist: %s %s" % (kwargs["slug"], e))
        raise Http404

    # Gather display for article.
    context["article"] = currentArticle
    
    # Gather display for related articles.
    context["related_articles"] = getRelatedArticles(currentArticle)
    
    return render_into_skin("articledir_view.html", RequestContext(request, context), request)

def requestList(request, **kwargs):
    '''
    Display a list of articles.
    
    If a tag is provided, only show articles under that tag. Otherwise, show all articles.
    '''
    context = {}
    
    # Fetch current tag, if available.
    currentTag = None
    if "slug" in kwargs:
        try:
            currentTag = Tag.objects.get(slug=kwargs["slug"])
            context["current_tag"] = currentTag
        except Tag.DoesNotExist,e:
            logging.error("Tag does not exist: %s %s" % (currentTag, e))
            raise Http404
    
    # Fetch all articles.
    # TODO: support article categories (with pretty images).
    articles = Article.objects.live().order_by("-publish_date")
    
    if currentTag:
        articles = articles.filter(tags=currentTag)
    
    # Paginate articles. Only show 10 per page, as we'll be displaying summaries.
    ARTICLES_PER_PAGE = 10
    currentBaseUrl = request.get_full_path().split("?")[0] # Remove any page numbres as get variables.
    (paginator_context, currentPage) = functions.getPaginatorContext(request,
                                                                     articles, 
                                                                     # Did this to strip page info from base url
                                                                     currentBaseUrl,
                                                                     ARTICLES_PER_PAGE)
                                                           
    context["paginator_context"] = paginator_context
    
    # Create display data for articles.
    articles = list(currentPage.object_list)
    
    # Shuffle articles if a tag is specified. This improves the uniqueness of each tag page (hopefully).
    if currentTag:
        random.seed(currentTag.id)
        random.shuffle(articles)
    
    context["articles"] = articles
    
    # Create display data for tags.
    context["tags"] = Tag.objects.all()
    
    return render_into_skin("articledir_list.html", RequestContext(request, context), request)

def searchArticles(sender, **kwargs):
    '''
    Hook for searching articles.
    TODO: search article content.
    '''
    group = AskbotSearchGroup("Articles", 2)
    query = kwargs["query"]
    for article in Article.objects.filter(title__icontains=query):
        result = AskbotSearchResult(article.title, getArticleUrl(article), None)
        group.addSearchResult(result)
    
    return group
    
search_askbot_signal.connect(searchArticles)