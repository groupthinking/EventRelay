# Unknown Video

## 📺 Video Information
- **Channel**: Unknown
- **Duration**: Unknown
- **Views**: 0
- **Published**: Unknown
- **Category**: General

## 🎯 Content Summary
Analysis not available

## 🔑 Key Concepts
Concepts not available

## 💻 Technical Details
Technical details not available

## 🛤️ Learning Path
Learning path not available

## 🚀 Code Generation Potential
Potential not analyzed

## 📊 Difficulty & Prerequisites
- **Level**: Unknown
- **Prerequisites**: None specified

## 🔗 Related Topics
Related topics not available

## 📝 Transcript
Hey, what's up YouTube, my name is Jake Krieger. 
And this is exactly what you think it is, it's   an introduction to flask for Python. So, this is 
what we're going to be doing here, I'm pretty much   going to start from the ground up, and we're going 
to go through each building block of flask until   we have created a basic crud application, it's not 
going to be anything too special, don't get Don't   get excited, it's just going to be a little like 
to do task master app. And then finally, we'll   top it off by deploying to Heroku. I feel like I 
should mention now before we continue on here that   this tutorial does assume some prior knowledge 
of Python, how Python code is written. It also   assumes you know, HTML CSS, you don't have to know 
it too well. For this tutorial, we don't write   a whole lot. But knowing how to write a basic 
HTML page would certainly be helpful. Otherwise,   it's pretty bare bones, you should be able to 
follow along pretty easily if you know how to   write code in general. Alright, so this is what 
we're actually going to be making here. A little   application called task master, it's basically 
just a to do list. Alright, as you can see, it   says you have no new tasks, create one below. So 
let's do that. Do the dishes. So as you can see,   it pops up in a little table, here, we've got our 
task, the date, it was added in some actions. So   we've got a delete action and an update action. 
Let's go ahead and check out the update action   here brings us to a new page where we can do 
exactly what you would think, update the task. So   I'm just gonna go ahead and change this to do the 
dishes and the laundry, click Update. And there   you go, it's updated in the table, do the dishes 
and the laundry. And then if we had completed it,   and we don't want it on our list anymore, we can 
just click Delete. There it goes. Alright, so   that's what we're going to be creating. Alright, 
so let's start with setting up our environment.   So we need to install Python, obviously 3.6. or 
newer, I believe the current version is 3.7 point   something. And then we're going to install the 
virtual and virtual environment package from Pip.   We're going to create our project directory, 
setup folders, all of that, create a virtual   environment. And then we're going to install the 
required packages. And that should be enough to   get us going. So let's do that. So we'll start by 
just typing in Python into Google here, head over   to python.org. Go to download and just click the 
link. If you're on Mac or Linux, you have Python   installed already. It should be python 2.7. I 
don't remember if Python three comes installed   already. But as you can see, I have Python 2.7 
installed. And I also have Python 3.6 point one,   so I'm good. And this is how you check your 
current version here. If you're on Mac or Linux,   the command corresponds to the version. So you 
use Python if you want to use Python 2.7 and   use the Python three command if you want to use 
Python three if you haven't installed. And this   is the same for PIP you use PIP if you're 
installing packages for Python two, and you   use PIP three if you're installing packages for 
Python three. Alright, so I already have Python   installed. So I don't have to click download. 
The next thing we need to do is actually set   up our work environment. So I'm in Visual Studio 
code here. Use whatever text editor ID you like,   I would strongly recommend Visual Studio Code 
though I think it's by far the most powerful,   the easiest to use quickest workflow. Anyways, 
I'm going to go ahead and click open folder   here. I'm just going to go ahead and actually, 
I'm already in my projects folder. So this is   fine. But this wherever you'd like, I'm gonna 
go ahead and call this flask introduction. And   then just click Open. And then I can close that. 
And then hit Ctrl tilde a to open up a terminal   here in our current folder. And I'm going to 
go ahead and type PIP three, install, whoops,   virtual ENB virtual env. And I already have this 
installed. So this is going to go really quick,   you most likely won't. And this is going to be 
what allows us to create a virtual environment   here. And if you're wondering why we do that, 
and don't just install the packages globally,   it's so that if we wanted to work with 
other people, if we wanted to, you know,   work on a project collaborate. It makes it so 
that all of the requirements all the packages   that are needed, are contained within the project 
itself and not on your system. In other words,   So you can transfer the project around and 
everyone can just install the requirements into   the working directory and have the exact setup 
that you had. So it makes it easier to work with   other people. And that's that's pretty much the 
gist of it. So that's what we're gonna do. So now   that we have virtual and installed, we're gonna go 
ahead and type virtual whoops, virtual and E and   V, and E and v is the name, as you can see, just 
popped up here, that could really be any name,   you want u and v is the convention, it's 
short, you'll have to type it. So Alright,   next up, we need to activate the environment. 
So we're going to go ahead and type source,   NV bin and activate and hit Enter. And as you can 
see, this little E and V in parentheses appeared.   That's how we know we are now inside of our 
virtual environment. So anything we do, or install   for Python will be contained inside of this 
environment and won't install anywhere globally   on our system. So let's go ahead and install the 
requirements. So just go into PIP three, install,   and we need flask. And we need flask whoops, flask 
SQL alchemy, like that, I'm gonna go ahead and hit   Enter. And that's going to install everything 
we need. Alright, now that that's installed,   I'm going to go ahead and create a new file here, 
I'm going to call it app.pi. I'm going to hit   Enter. And I'm going to go ahead and start writing 
a very, very basic, the most basic flask app you   can write, but it's going to give us an outline 
for the entire application. So before I do that,   just so you guys can see, I'm going to go ahead 
and up the font size, I think 18 should be pretty   big. Yeah, that works. Okay, so the first thing we 
need to do is import flask. So we're going to type   from flask, import flask with a capital F. Next, 
we need to set up our application. So we're going   to go ahead and type AB equals flask. And then in 
here, we're going to put underscore, underscore,   name, underscore, underscore. And that's just 
referencing this file. So next up, we need to   create a index route so that when we browse to the 
URL, we don't immediately just 404. And in flask,   you set up routes with the app route decorator. 
So app dot route. And then in here, you're just   going to pass in the URL string of your route. 
And we're gonna hit Enter. And then we're going   to define the function for that route. So we're 
just going to call this index. And for now,   we're just going to return a string. So hello, 
world. And then finally, we're going to type   if underscore underscore name, whoops, equals 
equals, underscore, underscore, main underscore,   underscore, app, run. And then for now, we're 
going to set debugging equal to true. So if we   have any errors, they'll pop up on the web page, 
and we can see. So that's pretty much it. That   is a very basic flask application, if we run this, 
it should work, it should pull up a page that says   hello world. So let's go ahead and see if that is 
the case. Come down to my terminal. And I'm going   to execute this with Python three. So I'm going to 
type Python three, app. Pi, come on. There we go.   And starts up a web server here. So just localhost 
and then the Port 5000. And there you go. Hello,   world. So as you could tell, it's pretty boring so 
far. So let's spice it up. Let's, let's talk about   static content. We'll go over some templates, 
we'll go over how to use CSS and JavaScript. So   let's create some new folders. Here, we're going 
to create two, we're going to call the first   one static. And then we're going to make one more 
and we're going to call this templates. And we're   going to go up to here at our import. And we're 
going to also import render underscore template.   So let's create a new file in here, we're going 
to call it index dot HTML. And come over to here,   we're going to change this from return string 
to return render template. We're gonna call that   file index dot HTML. And you don't have to specify 
the folder. The name is that name for a reason it   knows to look in that folder. So it's just the 
name of the file. We're just gonna create some   boilerplate HTML here. Just type Hello, world two. 
So we know our template is what we're seeing and   not that string anymore. So as you can see down 
here, it's automatically updating so we should   be able to refresh and see We are now reading 
from our template hello world two. Alright,   so let's talk about template inheritance. Now, 
if you don't know what that is, it's basically,   you create one master HTML file that that contains 
kind of the the skeleton of what each page is   going to look like. And then you just inherit 
that in each other page, and insert code where   you need it. But it's it basically makes it so 
you don't have to write this every single time,   you only have to write like this, and this what's 
relevant. So if that didn't make sense, go ahead   and show you how it's done. Call it base dot html. 
Alright, so this is going to be our skeleton. So   let's create the boilerplate code here. And then 
I'm just going to get rid of this title. And I'm   going to create a block I'm going to call it head. 
And I'm going to whoops. And the block. Alright,   so What's this doing? This is Jinja. To syntax. 
This is a template engine that flask uses. So   basically, what we're doing here is we're 
creating a block in the template. And this   block is where we're going to insert our code on 
all the other pages that inherit this template. So   this is pretty much outlining where we're going to 
insert our own code for each page. So I'm going to   make one more and I'm going to call this body. 
And then I'm going to come over to index here,   I'm going to get rid of all of this. And I'm going 
to come up here, whoops, and type extends. And   then in quotes, I'm going to put the name of the 
base template here, then I'm going to copy these   blocks that Enter, Enter. There we go. Okay, so 
now, I can put whatever I want here. So let's   create a Hey, so let's create a h1. And we'll just 
say, template. Sure. And now, if I load this up,   we should see template. So that's not all that 
special. You probably think that seems like a lot   of work just to get pretty much what we just had. 
But this is all you have to do for every page for   pretty much the rest of your website. As long as 
it follows this format, then that includes things   like linking stylesheets and scripts that can all 
be done over here. So you only ever have to do it   once. I just realized I had the the header in 
the head tag here. My bad. should still work.   Yep. Okay. All right. So now that we got templates 
work in here, let's go ahead and talk about static   content. So I'm gonna go over to our static 
folder, I'm gonna make a new folder in here,   called CSS. I'm gonna make a new file, and call 
it main dot CSS. And I'm just gonna put some basic   rule sets in here. So body. Alright, there we 
go. So just getting rid of the margin setting the   font family to Sancerre. Let's go ahead and link 
this in our base HTML. So we're going to do link   REL. All right, and then in the URL here, we can't 
just type something like static CSS main dot CSS,   this won't work. So what do we have to do, we 
have to use some more Jinja two syntax here.   If you remember before, who actually it's in his 
page, we were using the bracket percent. This is   for stuff like if else statements for loops. And 
these are for things you want to be printed in,   I guess strings. So this is basically going 
to take the code you write in here, and it's   going to give you the the result of that as a 
string. So we need to use a function from flask   called URL for and I don't know if we have to do 
this, but I'm gonna go ahead and do it anyways,   just import URL for and then I'm going to put 
parentheses here. And then I'm going to put in   quotes here single quotes because this is a double 
quote. I'm going to put the name of the static   folder static. I'm going to type file name, equals 
and then more single quotes. And I'm going to type   the name of the file and you have to include any 
subdirectories in this. So since it's static CSS,   main dot CSS, we have to put that in the file 
name. So CSS slash main dot CSS. And that should   be enough to link that stylesheet. So let's go 
ahead and see. And there you go. Sans Serif,   no margin, it's right up against the edge is 
linking our stylesheet. And this is the exact   same thing for JavaScript Do you it would just be 
file name equals j s slash main j. s, if that was   the name of your JavaScript that you're trying 
to link. Alright, so that does it for the basic   flask application. All right, I think we're ready 
to talk about databases now. So I'm gonna go ahead   and import SQL alchemy. So from flask, underscore 
SQL alchemy, import SQL alchemy. Alright,   let's go under our app here. And we're going to 
add a config. And this is going to be SQL alchemy   database URL. So this is telling our app where 
our database is located. And we're just going   to be using SQL Lite. There are lots of resources 
online for showing you how to do this with MySQL,   or Postgres, or whatever you want to use. But just 
to keep things simple, we're just going to use SQL   Lite. So we're just going to go ahead and type SQL 
eight, colon, and then three forward slashes for   forward slashes is an absolute path. Three is 
a relative path, we want a relative path here,   because I don't want to have to specify an 
exact location, I just want it to reside in   the project location. So I'm just going to go 
ahead and call this test.db. So that's what our   database is going to be everything is going to 
be stored in this test.db file. And then finally,   we need to initialize our database. So we're just 
going to type SQL alchemy app, pass in our app   like that. So our database has been initialized 
with the settings from our app. Alright,   so that's initializing the database. Now we need 
to create a model here. So we're going to make a   class and I'm just going to call this to do and 
this is a DB dot model like that. give myself   another new line there. Alright, now that we've 
got our class, let's set up some columns. So the   first one we need is an ID column, this is just 
going to be an integer that references the ID of   each entry. So this is of type DB column, and then 
this is an integer. And so this is going to be our   primary key. So we're going to set primary key 
equals to true. And then we're going to create a   text column here called content. And this is just 
going to be what holds each task. So this will be   DB dot string. And then I'll say 200 characters, 
I think is a good amount. And then I'm going to   set nullable equal to false, because we don't want 
this to be left blank, we don't want the user to   be able to create a new task, and then just leave 
the content of that task empty. So then finally,   we just need one more called date created. And 
this is more for bookkeeping than anything,   it's not something the user really needs access 
to. So this is going to be DB dot date time   like that with the capital T. And then we're 
going to set the default here. Got to come up   to the top real quick and import date time. So 
from date, time, import date, time. And then   we're gonna set the default equal to date, 
time, UTC now, okay. Alright, so basically,   any time and new to do entry is created, the date 
created will just automatically be set to the   time that it was created. So this we don't ever 
have to set manually, it'll always just be set   automatically. Alright, and then finally, we just 
need a function that's going to return a string   every time we create a new element. So we're gonna 
go ahead and tell it what to return here. And we   want it to return task. And then we'll just call 
self.id. So every time we make a new element,   it's just going to return task and then the idea 
of that task that's just been created. And that   does it for our model here. So let's go ahead 
and set up the database. Now. We're gonna head   down to the terminal. And I'm going to just type 
actually, first I have to activate my environment.   So let's do that. We begin, activate. There we 
go. Okay, so now that our environments activated,   we can go ahead and just start a interactive 
Python three shell So I'm going to type from app   import dB. So this is going to go ahead and import 
into our interactive shell, this DB object up   here. So then we're just going to type DB create, 
underscore all. And that should create a database.   And you can see it popped up right over here. So 
then we can exit out of that. And now we have our   database setup. If you remember from earlier, 
I showed you that task master application,   we're going to go ahead and create that now. 
Alright, so in our index dot HTML file here,   let's go ahead and get rid of this header. And 
I'm going to go ahead and set up a div here. I'm   just going to call this content. And then we're 
going to make a header, just call us or just have   the say task master. And I'm going to come down 
here, I'm going to make a table. Let's create a   table row, table header task. And then added for 
the date that it was created. And then actions,   oops. Okay, so that's, those are the three columns 
we'll have. And then I'm just going to leave this   empty for now we'll come back to this. Actually, 
you know what, I'm going to do this, I'm going   to create another row. And then I'm not going 
to put anything in here and make another one,   I'm gonna make one more. And then I'm going to add 
two links here. And I'm going to leave these empty   for now. Just have the, say, delete. Add a break 
here, and paste one more in and this one will say,   update. Okay, so let's go ahead and run our server 
here and see what we've got now. Okay, so there   we go. So as taskmaster, we've got a table. And 
we've got some links here for the actions, delete,   and update. Alright, so let's head on over to 
app.pi here. And we're going to come down to our   index and we need to change something, we need to 
come up into our decorator. And after the route,   we're going to add an option called methods. And 
then we're gonna set this equal to list here,   and this is going to be post in quotes, and then 
get in quotes. So this is adding two methods that   this route can accept. Now instead of just get by 
default, we can now post to this route as well and   send data to our database, which is exactly what 
we want to do. So let's head over to our index   file here. And then under table, we're going to 
add a form. And we're just going to set the action   URL to our index. And then method equals whoops, 
post. Alright, and then let's create two inputs,   we're gonna have a text input and a submit input. 
So text, set the name equal to content. And the ID   is also content. And the input again, type is 
submit value, add task. Alright, so those are   our two inputs for form, just go ahead and look 
at this. And it updated. But everything is now   all messed up. That's okay, we'll fix that later. 
not worried about it right now. All that matters   is that and we've now got the form that we need. 
All right, so let's go over this one more time.   Nothing in the head tag for now, we can actually, 
we can add a title, if you want, I'll just call   this task master. update this and yeah, it says 
task master. Okay, so that doesn't matter. You   can put whatever you want there. But uh, got a 
div here, called content. header, taskmaster,   you could say whatever you'd like. And then we're 
just creating a table. So I'm going to collapse   this for now. So we can get the whole thing in 
there. So these are headers task added in actions,   and then we've got one more row. And we've just 
kind of written the skeleton for this for now,   because this is going to be where each new task is 
added. So this is going to be updated dynamically,   which we haven't gotten to yet, but we will in 
just a moment. Alright, that's pretty much it   for the HTML for now. So let's head back to our 
app.py file. And then we're going to come down   to our index route here and we're gonna we're 
gonna Change this a little bit. So we're gonna   start with an if statement if request dot method 
equals equals post. So this is going to say if   the request that's set to this route is post, do 
stuff there, and then else, do more stuff. So this   is pretty much what we're looking at if post, this 
is how we're going to grab the task and put it in   our database. Otherwise, we're just pretty much 
looking at the page. So under else here, we can   actually just put render template and just have 
it show us our page. So this should work. Well,   it won't, because we're not running it. So let's 
do that first. Alright, name error request is not   defined, come up to our import here, and we just 
need to import that. And that should fix that. And   there we go. So it's still just showing us our 
page. And then, if we were to submit that form,   type error, the view function did not return 
a valid response, because we're not actually   returning anything. If I set this to return Hello, 
that should do exactly what it says. It'll return   Hello, if we submit our form, otherwise, it's just 
going to show us our page. So we've set that up.   So let's go ahead and actually put our logic for 
adding a task in here, let's create a variable,   we're gonna call this task content. And then 
that request object again, form for that form   we created. And then we're just going to pass 
in the ID of the input that we want to get the   contents of which was content. So test content is 
equal to the contents of this input right here.   So then I'm just going to go ahead and create a 
model for this. As you can see, our we have our   to do model. So let's create a to do object that's 
going to have its contents equal to the content of   that input. So now we've got our to do model, all 
that's left to do is push it to our database. So   we're going to try DB dot session dot add. So 
we're adding this to our database session, this   new task, then we want to commit so DB dot session 
dot commit, commit that to our database. And then   finally, we just need to return. And we're going 
to return a redirect back to our index, which we   have to come back up to our import again, and now 
we're going to import redirect. So it's going to   create a new task from that input, it's going to 
try to commit it to our database, and then it's   going to redirect us back to our index page. If 
that does happen to fail, just create an accept   here and we're just going to return there was an 
issue, adding your test. So just a plain string,   with the error message here is all we really 
need. This should, generally speaking, never fail,   but just in case it does. And then we're going 
to come down to lcwr. And we're going to create   a variable called tasks, set this to a to do query 
order, underscore by to do dot date created. So   what is this, this is going to look at all of the 
database contents in the order they were created.   And it's just going to return all of them. So 
we're just querying our database or ordering them   by the date created, so newest to oldest and then 
we're just grabbing all of them. You could also do   first to grab the first, which would be the most 
recent if we're sorting by date, we're just going   to grab them all. And this is how we're going to 
display all the current tasks in that table. And   then we need to pass this to our template. And 
we're just going to set tasks equal to tasks,   that variable we just created. And that does it 
for our index form. So let's head on over to the   index dot HTML. And we just need to add some quick 
code here. We're going to come down to this row,   I'm going to indent this. And then we're going to 
do some Jinja to syntax here. And then we're just   going to type for task in tasks. And this is going 
to grab all of the tasks in that task variable we   passed to this template. And then we just need to 
end the four. So we're just going to come up to   our first TD tag here and we're going to do double 
curly braces. And we're just going to type task   content. So this is going to return the content 
of Each task. And then we're just gonna do one   more for the date created. And then we're just 
going to do dot date. So it doesn't return the   time as well, because if you remember, it's a date 
time object right here, date time, we just need   the date. So a created date. And then over here, 
we actually haven't set up our delete route yet,   so I'm gonna leave that alone. But if I go ahead 
and start up our app here, could see our table   disappears. So let's go ahead and add a task. 
And as you can see, it pops up in our table.   So the Delete and update don't do anything yet. 
But as you can see, pushing to our database is   currently working. So we've got the Create part 
of our crud app done. So I'm just real quick,   I'm going to copy over some CSS to clean up this 
page a little bit as it's kind of just kind of not   very attractive sitting there all the way in the 
corner like that. Alright, so let me refresh here.   And there we go. So that's kind of what we were 
looking at originally, I'm actually going to go   ahead and just do this real quick. Go ahead and 
send her a line that text. So there we go. Okay,   so that's, that's what we had earlier. Alright, so 
now that we've got the Create part done, let's go   ahead and do the Delete part, because that's the 
next easiest. So let's head over to our app.pi.   And we need to set up a new route for this. So I'm 
just going to come under index one here, app that   route, and then it's going to be slash delete. And 
then we need to get the ID, this number right here   is going to be the easiest way of identifying 
a unique task. Because if we go by content or   anything like that, this kind of content can 
be the same for multiple passes. So we need a   unique identifier, which is what this primary 
keys here for, this will always be unique, you   can never have a duplicate. So come over to here, 
slash delete slash, and then we're going to put in   a bracket here, int for integer, colon, and then 
the name of the variable. So we're just gonna call   this ID. And then that's it for that. Alright, 
so then let's just find our function here. We'll   call it elite, passing ID as the variable 
that we need. And then we're ready to go.   So let's go ahead and create a variable for the 
task that we want to delete. So task to delete,   and then we're going to query our database here. 
And we're going to do get, so dot query dot get   underscore or underscore 404 ID. So this is going 
to attempt to get that task by the ID. And if it   doesn't exist, it's just going to four or four. So 
then let's do a try. Then we're going to do DB dot   session dot delete. And then we're going to pass 
in task to delete. Whoops, didn't mean to do that,   then we're going to come on to there, and we need 
to commit this again, commit. And then we're going   to return a redirect back to our homepage. And 
then if this doesn't work, we'll just print   another string with our error message. So there 
was a problem, deleting that task. Alright. So   that is our delete route. And this should actually 
work. I think we're good here. Let's go ahead and   run our app again. And we've got this task in 
here. Actually, no real quick, we do have to   come over to our delete. So let's do slash delete. 
And then double brackets here, because we want to   get the ID of that current task. So task.id. And 
that should, if we hover over this, you can see   down at the bottom left there in the browser, so 
slash delete slash one, so it's getting the idea   of this task. So if we click Delete, disappears, 
there we go. So that's the Delete. All right,   on to updating. So let's make one more route here. 
I'm gonna call it app dot route, slash update,   slash. And we're going to do the same thing and 
ID. So we're gonna grab the ID of the task we   want to update. And then methods. And we need to 
do the same thing as earlier with our index route,   because we're going to be posting. So let's go 
ahead and do that. And then let's go ahead and   create the function. So update ID. And then return 
for now just return nothing. Let's come over to   our index here, and we're going to copy this, 
paste it down here and instead of slash delete,   we'll change this to slash update. And then 
we're going to make one more template here and   we're going to call this update dot html. And 
we're going to just copy our index HTML here,   we're going to get rid of this table. Because we 
don't need to show all of our tasks, we just want   to show the one that we're updating, change this 
to update task. So then the action will be slash   update, slash. And then we'll grab that, whoops. 
hask Id like that. Okay, so this should be our   update page, we're gonna go over to our update 
route, I'm going to do if request dot method   equals post, pass, because we'll add our code 
in a minute here else, return render, template,   update. html. Okay. So there we go. I'm just gonna 
go ahead and run this real quick. And make sure   that if we go to, we need to make a new test task 
here, the update page. Okay, so it did work. It's   returning an error task is undefined because I've 
called task ID. But if you notice in our function   here, I'm not actually sending a variable called 
task. So let's come down. Actually, we'll do it up   here, we'll create a variable called task equals 
to do query. Think I typed that, right? Yep. That,   actually, we could just copy this whole thing. 
Okay, there we go. So same thing as the Delete,   we're grabbing the task. We're just getting the 
task from the ID here, because we're passing that   into the URL, then we'll come down to here, and 
we'll pass that into our render template function   here. And now this should work. There we go. So 
it's not grabbing the text from our task. As you   can see, it says do the dishes in the laundry. 
When we click Update, that's not in here. So   let's auto populate that, come over to update. 
And then we'll set the value of this input this   text input to grab this instead of task that it or 
ID task content. So now that should, there we go   show the text of the task. So then we want when we 
click Update, or well doesn't say update, because   we have to change that here. forgot about that. 
So there we go. Now if we click Update, it's not   doing anything, the view function did not return 
a valid response. Because if you remember, we're   just doing a pass here. So let's go ahead and add 
our update logic is actually pretty easy. Task   content equals request. form content. actually 
got this wrong past content, not task underscore   content, equals request frm. So we're just setting 
this current tasks content to be content in this   forum's input box. And then we just need to try 
DB dot session commit. And we don't have to add   or delete or anything, we just have to commit 
because we set the content right here. So we're   not adding a new one, we're just updating. And 
then we need to do a return redirect back to our   homepage. And that's it for that. So unexpected 
into Oh, it forgot our exception here. Return   there was an issue updating your task. Alright. 
should be good now. Yep. That mean to open   Chrome. Let's go ahead and update this task. So 
let's just change do the dishes and the laundry,   and brush your teeth. And click Update. And there 
you go. So we are now updating our task. Let's go   ahead and make another task here. So we can see 
that there are multiple entries popping up in   this box here, do the dishes and E some broccoli. 
Definitely didn't spell that right. Brock. Oh,   Lee, we're going with we're going with two L's 
add task. So there we go. And then we can update   all of these individually. Let's change that to 
banana. Eat some banana. Doesn't make sense, but   it doesn't need to because we can just delete it. 
I'm going to delete that. And I'm going to delete   that. And now we have nothing. So I'm going to add 
one more thing to our index page. I'm going to add   an if statement. And Jinja to syntax. Alright, 
and this is going to say if tasks. And then   we're going to do a filter here. This is a Jinja 
to filter. It's called length He's going to get   us the length of that list. And if it's less 
than one, so if there are no entries in it, we   will go ahead and create one more here. And it's 
just going to say else. So if there are entries,   we want to show this table. But if there aren't 
any entries, we want to just show a header here   that says there are no tasks, create one below. 
And then close off that. And then we'll just copy   this center style here for that as well. So now, I 
think this is still updating, encountered unknown   tag and to block because we didn't end our if. So 
let's grab this end for here. Come under table.   And then change this from end to end if and now 
we should be good. There are no tests create one   below looks like there's some formatting issues 
for not totally sure how I managed to do that,   but should be good now. Okay, there we go. And 
then if we make a new task, do the dishes add   task that goes away, now we see our table. So I 
believe that's everything, we've got everything   working. So that is a basic crud app. All right. 
So finally, let's talk about pushing to Heroku.   If you don't know what Heroku is, I'll go ahead 
and show you go to Heroku comm it's pretty much a   service that lets you host any number of different 
web apps, whether it's Node JS, Ruby on Rails,   PHP, Python, that could be Django flask, what have 
you. And they'll they'll host your app for you and   pretty much run it off their own servers and not 
your own. So you can also create databases through   them. And it pretty much makes it really easy to 
manage and run a web app without having to set up   your own web server. So I already have an account, 
if you don't just go ahead and click Sign up and   sign up for free, they have a free tier, you will 
have to use your credit card if you want to add   any of their database functionality. But since we 
were just using SQL lite, we don't have to worry   about that. So free tier is fine. So yeah, just go 
ahead and sign up. And then once you've signed up,   go ahead and look up Heroku CLR, we need the 
command line interface here. And it's that first   link, just go ahead and click that come down to 
download and install here. And you can see there   are installers for whatever system you're on. 
So just go ahead and install that. And then once   that's installed, let's head down to our terminal 
here and type in Heroku log in. And that's going   to pull this up, I've already logged in before, so 
it knows my email if you probably haven't before,   so just go and type your sin and enter, type your 
password, hit Enter, and it should log you in just   like that. Alright, now that that's done, let's go 
ahead and create an empty Git repository. I feel   like I should mention that you do need Git. If you 
don't have Git installed, just go ahead and go to   get dash SCM comm and install it off of there. And 
then once that's installed, you'll be able to use   the Git command line as well. Actually, before we 
do that, we need to freeze our requirements. And   actually, before we do that, we need to install a 
dependency. So let's go ahead and make sure you're   in your virtual environment here, we're going to 
type PIP three, install, and it's called gunicorn,   Jiyu. And I corn, hit Enter. And go ahead and let 
that install should go pretty quick. And then you   can go ahead and freeze your requirements. 
So PIP three, freeze requirements dot txt,   and that's going to spit out all the requirements 
in a txt file here. And now that we're done with   that, we can go ahead and initialize an empty Git 
repository. So Git init. So initialized, empty Git   repository, git add and then period just to add 
everything in the directory. And then that's done.   So then we need to commit, I'll just say in the 
app for the comment here. And then that's going   to commit everything to the repository. So now 
we can finally create our Heroku app. So Heroku,   create. And then your application name, this can 
only be lowercase letters, can only have dashes   and numbers. So we're just going to create one 
called flask, crud app tutorial, and I'm gonna   hit enter, that's going to go ahead and create 
our app. So then we can type Git remote dash V,   and we can see where we're pushing to, so 
get to Heroku COMM And then we're pushing   that application we just created. So let's type 
git push Heroku Master, hit Enter. And finally,   this is going to push everything to Heroku. And 
I actually just realized we're missing a crucial   file here. So I'm going to let this finish up 
and it's not going to work. And I will show you   why in just a second. All right, so it finished 
but It's not going to work, I'm going to go ahead   and open it up anyways, I'm just going to copy 
that into a browser, type that in and hit Enter,   and we get an application error. Why do we get an 
application error? Well, we're missing a file that   tells Heroku what to do with all these files, I 
pretty much just pushed a directory of files and   Heroku is just kind of sitting there. twiddling 
its thumbs not knowing what to do with them. So   we got to tell it what to do with them. So we 
need to create a file called a proc file. So   I'm just gonna go ahead and pipe touch proc file 
with a capital P, there's no extension, it's just   proc file. And then we need one line. It's really 
short web colon gunicorn. So we're going to call   that library we installed. Well, it's not really 
a library. And so it creates a web server. And   then we need to tell it, what file to create a 
web server for. So our app file app colon app.   And that's it. So now if we get add everything, 
git commit, dash m, added proc file, git push   Roku Master, hit Enter. And now it should work. So 
I'm going to go ahead and let this do its thing.   And then when I return, hopefully, we'll have a 
working web app on the internet. All right, so   here we go. Let's go ahead and check this out. And 
there you have it. Well, we should probably make   sure it works first. So I'm gonna go ahead and 
add do the dishes. Looks like it popped up there.   See if update works, do the dishes and eat some 
broccoli. Looks like that's working. Let's see   if we can delete it. And there we go. Looks like 
everything's working. And as you can see, this is   running on HTTPS at our application URL. So this 
is running on a live web server. Alright, thanks,   everyone for watching. That does it. This Git 
repository will be available. Hopefully, it'll be   in the description. I hope you learned something. 
I hope it was helpful. And I'll see you around.

---
*Generated by UVAI Enhanced Video Processor using Google Gemini API*
*Processing Time: 2025-11-08T02:37:00.927521*
*Pipeline: Enhanced Gemini + LiveKit + Mozilla AI Tools*
