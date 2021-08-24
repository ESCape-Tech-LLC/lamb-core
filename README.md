# Lamb REST Framework 

## 1.Installation

### A. Install using `pip`...

	pip install git+https://bitbucket.org/kovsyk/lamb-core.git#egg=lamb
	
	or via requirements.txt
	
	...
	git+https://bitbucket.org/kovsyk/lamb-core.git#egg=lamb
	...
	
### B. Add `lamb` to your project via settings.py:
	
	INSTALLED_APPS = [
		...
    	'lamb'
	]
	
	MIDDLEWARE = [
    	'django.middleware.common.CommonMiddleware',
    	...
    	'lamb.db.middleware.SQLAlchemyMiddleware',
    	'lamb.rest.middleware.LambRestApiJsonMiddleware',
	]
	
Also example would require some additional data in `settings.py`:
	
	# Static folders and urls
	LAMB_STATIC_FOLDER = os.path.join(BASE_DIR, 'static/')
	LAMB_SYSTEM_STATIC_FOLDER = os.path.join(BASE_DIR, 'system-static/')
	LAMB_TEMPLATES_FOLDER = os.path.join(LAMB_SYSTEM_STATIC_FOLDER, 'templates/')
	LAMB_LOGS_FOLDER = os.path.join(BASE_DIR, 'logs')
	
	LAMB_IMAGE_UPLOAD_ENGINE = 'lamb.service.image.uploaders.ImageUploadServiceDisk'
	
	LAMB_REST_APPLIED_APPS = [
	    'api'
	]

## 2. Basic usage 

### A. Create API layer module
Create new module that would be responsible for your API, for example module `api` with structure:

	api/
		urls.py
		views.py
		model.py
		__init__.py

Add this module to `INSTALLED_APPS`:

	INSTALLED_APPS = [
		...
    	'api'
	]

### B. Declare your model in `model.py`
Let's decalre for example simple model for books with zero or more optional illustrations:
	
    class TablePrefixMixin(TableConfigMixin):
        @declared_attr
        def __tablename__(cls):
            result = super(TablePrefixMixin, cls).__tablename__
            return "test_app_" + result
    
    
    class Book(ResponseEncodableMixin, TablePrefixMixin, DeclarativeBase):
        # columns
        book_id = Column(UUIDType(binary=False, native=True), nullable=False, default=uuid.uuid4, primary_key=True)
        title = Column(VARCHAR(300), nullable=False)
        isbn = Column(VARCHAR(100), nullable=False)
    
        # relations
        illustrations = relationship('Illustration', cascade='all')
    
    
    class Illustration(TablePrefixMixin, AbstractImage):
        __slicing__: List[ImageUploadSlice] = [
            ImageUploadSlice('origin', -1, ImageUploadMode.NoAction, ''),
            ImageUploadSlice('small', 100, ImageUploadMode.Resize, 'small'),
            ImageUploadSlice('thumb', 50, ImageUploadMode.Crop, 'thumb')
        ]
    
        # columns
        book_id = Column(UUIDType(binary=False, native=True),
                         ForeignKey(Book.book_id, onupdate='CASCADE', ondelete='CASCADE'),
                         nullable=False)
    
        __mapper_args__ = {
            'polymorphic_identity': 'illustration',
            'polymorphic_on': AbstractImage.image_type,
        }

	    
### C. Create your model in database

#### Create database first
Create your database and user if required. For example on MySQL:

	# create user
	DROP USER 'books_user'@'localhost';
	CREATE USER 'books_user'@'localhost' IDENTIFIED BY 'vR0Q9UxKRqPFZpB';

	# create database
	DROP DATABASE books;
	CREATE DATABASE IF NOT EXISTS books CHARACTER SET utf8 COLLATE utf8_general_ci;
	GRANT ALL ON books.* TO 'books_user'@'localhost';
	use books;

#### Declare connection in settings.py
Define required connection params in `databases` section of `settings.py`:

	DATABASES = {
	    'default':{
	        'ENGINE': 'django.db.backends.mysql',
	        'NAME': 'books',
	        'USER': 'books_user',
	        'PASSWORD': 'vR0Q9UxKRqPFZpB',
	        'HOST': 'localhost'
	    }
	}

	
####  Create your model in database
In terminal under project virtualenv: 

	python manage.py alchemy_create api
	
Generally syntax work in next way:

	python manage.py alchemy_create <module to fetch available models>
	
### D. Create views that realize your API
In api/views.py declare:

	from api.model import *
	from lamb.rest.rest_view import RestView
	from lamb.rest.decorators import rest_allowed_http_methods
	from lamb.utils import dpath_value, parse_body_as_json
	from lamb.json.response import JsonResponse
	
	@rest_allowed_http_methods(['GET', 'POST'])
	class BookListView(RestView):
	
	    def get(self, request):
	        db_session = request.lamb_db_session
	        return db_session.query(Book).all()
	
	    def post(self, request):
	        db_session = request.lamb_db_session
	        json_body = parse_body_as_json(request)
	
	        book = Book()
	        book.title = dpath_value(json_body, 'title', str)
	        book.isbn = dpath_value(json_body, 'isbn', str)
	
	        db_session.add(book)
	        db_session.commit()
	        return JsonResponse(book, status=201)
	
	@rest_allowed_http_methods(['GET', 'PATCH', 'DELETE'])
	class BookView(RestView):
	    def _find_book(self, request, book_id):
	        db_session = request.lamb_db_session
	        book = db_session.query(Book).get(book_id)
	        return book
	
	    def get(self, request, book_id):
	        return self._find_book(request, book_id)
	
	    def patch(self, request, book_id):
	        book = self._find_book(request, book_id)
	
	        json_body = parse_body_as_json(request)
	        book.title = dpath_value(json_body, 'title', str)
	        book.isbn = dpath_value(json_body, 'isbn', str)
	
	        request.lamb_db_session.commit()
	        return book
	
	    def delete(self, request, book_id):
	        book = self._find_book(request, book_id)
	
	        request.lamb_db_session.delete(book)
	        request.lamb_db_session.commit()
	        return JsonResponse(status=204)
	        
### E. Declare url endpoints
`api/urls.py:`

	from django.conf.urls import url
	from api.views import *
	
	app_name = 'api'

	urlpatterns = [
	    url(r'^books/?$', BookListView, name='book_list'),
	    url(r'^books/(?P<book_id>[\w-]+)/?$', BookView, name='book')
	]
	
Also include API urls in project url configs in `<project_name>/urls.py`:

	from django.conf.urls import url,include
	
	urlpatterns = [
		...
	    # API
	    url(r'^api/', include('api.urls', namespace='api', app_name='api')),
	]
	
	handler404 = 'lamb.utils.default_views.page_not_found'

	handler400 = 'lamb.utils.default_views.bad_request'

	handler500 = 'lamb.utils.default_views.server_error'

	
### F. Check work
Run your server and try send some requests to declared endpoints for testing purpose.

#### Add new book:
HTTP Request:

	POST /api/books/ HTTP/1.1
	Host: localhost:8000
	Content-Type: application/json
	Cache-Control: no-cache
	
	{
		"title":"new book",
		"isbn":"1234567890"
	}

Will generate response:
	
	{
	  "book_id": "97b80553-a0ba-427b-987c-7aa7581cc563",
	  "title": "new book",
	  "isbn": "1234567890"
	}
	
#### Get list of books:
Create several books before run next request.

HTTP Request:

	GET /api/books/ HTTP/1.1
	Host: localhost:8000
	Content-Type: application/json
	Cache-Control: no-cache

Will generate response:
	
	[
	  {
	    "book_id": "2964f6d3-30c9-4743-8323-2d434e71b4e5",
	    "title": "new book 2",
	    "isbn": "1234567890"
	  },
	  {
	    "book_id": "64379882-f6af-465e-b156-98b57b2526de",
	    "title": "new book 3",
	    "isbn": "1234567890"
	  },
	  {
	    "book_id": "97b80553-a0ba-427b-987c-7aa7581cc563",
	    "title": "new book",
	    "isbn": "1234567890"
	  }
	]
	
	
#### Invalid request error format
Let's try to call for unsupported service - PUT

HTTP Reqeust:
	
	PUT /api/books/ HTTP/1.1
	Host: localhost:8000
	Content-Type: application/json
	Cache-Control: no-cache

Will generate response:
	
	{
	  "error_code": 1,
	  "error_message": "HTTP method PUT is not allowed for path=/api/books/. Allowed methods (GET,POST)",
	  "details": null
	}
	

# Release notes:

2.1.18:
- feature: support for `SESSION_OPTS` in project database connection

2.4.3:
- fix: json encode date-format in case of `orjson` available
- fix: update `celery` dependency for latest binary compatible version
