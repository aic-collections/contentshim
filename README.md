# Getting Started

~~~bash
virtualenv -p python3 csenv
cd csenv
. bin/activate
git clone https://github.com/aic-collections/contentshim.git
cd contentshim
pip install -r requirements.txt
~~~

At this point you will need to modify at least one file to get going:

~~~bash
cp config/local.yaml.default config/local.yaml
~~~
Open the file for editing and make changes as needed.  Minimally, 
the `app_base_path` base value will have to be changed.  Check the 
fedora HTTP path.  The remaining should be OK to get going.

You can now start the Content Shim:

~~~bash
./bin/flask-server.sh --config config/local.yaml
~~~

# Bootstrapping

Once the server is running you will need to initialize the database.  The Content
Shim uses `sqlite`.  While this solution may not seem robust enough, bear in mind 
that there is a single table of all of three columns.  It works rather spendidly 
for a major US art museum's website; perhaps you have more images to serve. YMMV.

~~~bash
curl -i -X GET http://host:port/initdb
~~~

# Running in production

Gunicorn - a WSGI HTTP Server - can be used for production.  You will need to modify
at least two additional files:

~~~bash
cp config/gunicorn_prod.py.default config/gunicorn_prod.py
cp app/wsgi.py.default app/wsgi.py
~~~

Open each file and edit as needed.

We have an Apache HTTP server running out front proxying the Content Shim.

# Cantaloupe Integration

[Cantaloupe's documentation](https://medusa-project.github.io/cantaloupe/manual/3.3/) 
is fantastic.  Way better than what you are reading.  You should consult it first.

To use this Content Shim, we require the use of the [`delegate.rb` script](https://medusa-project.github.io/cantaloupe/manual/3.1/delegate-script.html)
feature of Cantaloupe.  Basically, Cantaloupe is configured to use the `delegate.rb` 
script, which can be readily configured via Cantaloupe's `cantaloupe.properties` file.
With it, you can provide specific instructions about where Cantaloupe should locate
the file that will ultimately be served.  In our case, we opted for the [FileResolver Script
Lookup Stragtegy](https://medusa-project.github.io/cantaloupe/manual/3.1/resolvers.html#FilesystemResolverScriptLookupStrategy).
Specifically, our custom FileSystemResolver looks like the following:

~~~ruby
  module FilesystemResolver

    ##
    # @param identifier [String] Image identifier
    # @return [String,nil] Absolute pathname of the image corresponding to the
    #                      given identifier, or nil if not found.
    #
    def self.get_pathname(identifier)
        uri = 'http://localhost:8000/images/' + CGI.escape(identifier) + '/fspath'
        uri = URI.parse(uri)

        http = Net::HTTP.new(uri.host, uri.port)
        request = Net::HTTP::Get.new(uri.request_uri)
        response = http.request(request)
        return nil if response.code.to_i >= 400
        (response.body.length > 0) ? response.body.strip : nil
    end

  end
~~~

# License

[AIC Copyright; Apache License 2.0](LICENSE)



