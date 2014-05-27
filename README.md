# Django Twisted Extensions - Core

`Django Twisted Extensions` is meant to add an ability to develop async request handlers
in `Django` projects

## Simple Example

#### urls.py
```py
urlpatterns = patterns('',
    url(r'^example/test/(?P<item_id>.*)/',
        'example.views.gw2test',
        { 'api': 'https://api.guildwars2.com/v1/' }
    ),
)
```

#### views.py
```py
@inlineCallbacks
def gw2test(request, item_id, api):
    x = yield getPage(api + 'item_details.json?item_id=' + str(item_id))
    details = json.loads(x)
    returnValue(HttpResponse(str(details['name']), content_type='text/plain'))
```

## License

MIT
