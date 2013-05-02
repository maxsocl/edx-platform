This is edX, a platform for online higher education. The project is primarily
written in [Python](http://python.org/), using the
[Django](https://www.djangoproject.com/) framework. We also use some 
[Ruby](http://www.ruby-lang.org/) and some [NodeJS](http://nodejs.org/).

Installation
============
The installation process is a bit messy at the moment. Here's a high-level
overview of what you should do to get started.

**TLDR:** There is a `create-dev-env.sh` script that will attempt to set all
of this up for you. If you're in a hurry, run that script. Otherwise, I suggest
that you understand what the script is doing, and why, by reading this document.

Directory Hierarchy
-------------------
This code assumes that it is checked out in a directory that has three sibling
directories: `data` (used for application data?), `db` (used to hold a
[sqlite](https://sqlite.org/) database), and `log` (used to hold logs). If you
clone the repository into a directory called `edx` inside of a directory
called `dev`, here's an example of how the directory hierarchy should look:

    * dev
     \
      * data
      * db
      * log
      * edx
       \
        README.md

Language Runtimes
-----------------
You'll need to be sure that you have Python 2.7, Ruby 1.9.3, and NodeJS
(latest stable) installed on your system. Some of these you can install
using your system's package manager: [homebrew](http://mxcl.github.io/homebrew/)
for Mac, [apt](http://wiki.debian.org/Apt) for Debian-based systems
(including Ubuntu), [rpm](http://www.rpm.org/) or [yum](http://yum.baseurl.org/)
for Red Hat based systems (including CentOS).

If your system's package manager gives you the wrong version of a language
runtime, then you'll need to use a versioning tool to install the correct version.
Usually, you'll need to do this for Ruby: you can use
[`rbenv`](https://github.com/sstephenson/rbenv) or [`rvm`](https://rvm.io/), but
typically `rbenv` is simpler. For Python, you can use
[`pythonz`](http://saghul.github.io/pythonz/),
and for Node, you can use [`nvm`](https://github.com/creationix/nvm).

Virtual Environments
--------------------
Often, different projects will have conflicting dependencies: for example, two
projects depending on two different, incompatible versions of a library. Clearly,
you can't have both versions installed and used on your machine simultaneously.
Virtual environments were created to solve this problem: by installing libraries
into an isolated environment, only projects that live inside the environment
will be able to see and use those libraries. Incompatible dependencies? Use
different virtual environments, and your problem is solved.

Once again, each language has a different implementation. Python has
[`virtualenv`](http://www.virtualenv.org/), Ruby has
[`bundler`](http://gembundler.com/), and Node has
[`nave`](https://github.com/isaacs/nave). For each language, decide
if you want to use a virtual environment, or if you want to install all the
language dependencies globally (and risk conflicts). I suggest you start with
installing things globally until and unless things break; you can always
switch over to a virtual environment later on.

Language Packages
-----------------
The Python libraries we use are listed in `requirements.txt`. The Ruby libraries
we use are listed in `Gemfile`. The Node libraries we use are listed in
`packages.json`. Python has a library installer called
[`pip`](http://www.pip-installer.org/), Ruby has a library installer called
[`gem`](https://rubygems.org/) (or `bundle` if you're using a virtual
environment), and Node has a library installer called
[`npm`](https://npmjs.org/).
Once you've got your languages and virtual environments set up, install
the libraries like so:

    $ pip install -r requirements.txt
    $ bundle install
    $ npm install

Configuring Your Project
------------------------
We use [`rake`](http://rake.rubyforge.org/) to execute common tasks in our
project. The `rake` tasks are defined in the `rakefile`, or you can run `rake -T`
to view a summary.

Before you run your project, you need to create a sqlite database and create
tables in that database. Fortunately, `rake` will do it for you! Just run:

    $ rake django-admin[syncdb]
    $ rake django-admin[migrate]

If you are running these commands using the [`zsh`](http://www.zsh.org/) shell,
zsh will assume that you are doing
[shell globbing](https://en.wikipedia.org/wiki/Glob_(programming)), search for
a file in your directory named `django-adminsyncdb` or `django-adminmigrate`,
and fail. To fix this, just surround the argument with quotation marks, so that
you're running `rake "django-admin[syncdb]"`.

Run Your Project
----------------
To *finally* get up and running, just run:

    $ rake cms

And `rake` will start up your Django project on the localhost, port 8001. To
view your running project, type `127.0.0.1:8001` into your web browser, and
you should see edX in all its glory!


Further Documentation
=====================
Once you've got your project up and running, you can check out the `docs`
directory to see more documentation about how edX is structured.



