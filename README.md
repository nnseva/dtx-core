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
    )
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

The MIT License (MIT)

Copyright (c) 2013, 2014 Alexander Zykov

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
