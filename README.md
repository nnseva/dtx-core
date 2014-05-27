### Django Twisted Extensions - Core

Django Twisted Extensions - Core

### Simple Example

urls.py
```py
urlpatterns = patterns('',
    url(r'^example/test/(?P<item_id>.*)/',
        'example.views.gw2test',
        { 'api': ''https://api.guildwars2.com/v1/'' }
    ),
)
```

views.py
```py
@inlineCallbacks
def gw2test(request, item_id, api):
    x = yield getPage(api + 'item_details.json?item_id=' + item_id)
    details = json.loads(x)
    returnValue(HttpResponse(str(details['name']), content_type='text/plain'))
```
