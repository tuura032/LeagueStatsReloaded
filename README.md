# LeagueStats

League Stats is a web application built to present users novel and relevant data. It is a Flask Application built with Python
and Bootstrap. The database was built with PosgreSQL and is hosted on Heroku. Data was primarily collected from the ESPN API or
web scraping using the BeautifulSoup library.


<strong>Primary Features</strong>

<ul>
<li>Home page displaying the most important data and newly created statistics; can also be sorted by week.</li>
<li>A page for each user, displaying data unique to their team.</li>
<li>Pages update automatically in response to database</li>
<li>Ability to update databases on page-load.</li>
<li>Data Visualization.</li>
 </ul>




<strong>Application</strong>

application.py is a Flask application that uses SQLAlchemy to access the database. This file hosts all of the routes that direct the user
to the appropriate page with the correct data queries.


<strong>getScoreBoardData</strong>

Contains all helper functions to either sort or get data to return to the given page.



<strong>Usage</strong>

While publicly viewable, this web app is intended only for private use.


