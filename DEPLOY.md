# Hosting on PythonAnywhere

PythonAnywhere's free plan runs Flask apps and includes a MySQL database. The site will be at
`https://YOUR_USERNAME.pythonanywhere.com`. Replace `YOUR_USERNAME` everywhere below with your
PythonAnywhere username.

## 1. Create the account and the database
1. Sign up for a free "Beginner" account at https://www.pythonanywhere.com.
2. Open the **Databases** tab. Set a MySQL password and write it down. This is a new password, not your login password.
3. Under "Create a database", enter `air_ticket` and click **Create**. PythonAnywhere names it `YOUR_USERNAME$air_ticket`.

## 2. Get the code
Open the **Consoles** tab and start a **Bash** console, then run:
```bash
git clone https://github.com/mahra-11/databases.git
```
```bash
cd databases
```
```bash
pip3.10 install --user -r requirements.txt
```

## 3. Load the tables and sample data
In the same console, run these two commands. Each one asks for the MySQL password from step 1.
```bash
mysql -u YOUR_USERNAME -h YOUR_USERNAME.mysql.pythonanywhere-services.com -p 'YOUR_USERNAME$air_ticket' < sql/schema.sql
```
```bash
mysql -u YOUR_USERNAME -h YOUR_USERNAME.mysql.pythonanywhere-services.com -p 'YOUR_USERNAME$air_ticket' < sql/sample_data.sql
```

## 4. Create the web app
1. Open the **Web** tab and click **Add a new web app**. Click Next.
2. Choose **Manual configuration** (not "Flask"), then **Python 3.10**.
3. On the web app page, set **Source code** to `/home/YOUR_USERNAME/databases`.
4. Click the link next to **WSGI configuration file**. Delete everything in it, paste in the contents of
   `deploy/pythonanywhere_wsgi.py`, and fill in your username, MySQL password and a random secret key. Click **Save**.
5. Under **Static files**, add URL `/static/` with directory `/home/YOUR_USERNAME/databases/static`.
6. Click the green **Reload** button at the top, then open `https://YOUR_USERNAME.pythonanywhere.com`.

If the site shows an error, the **Error log** link on the Web tab says why.

## Updating the site after changes
In a Bash console:
```bash
cd ~/databases && git pull
```
Then click **Reload** on the Web tab. To reset the sample data (fresh dates, test purchases removed),
run the two commands from step 3 again.

## Keep it running
Free web apps are switched off if nobody extends them. Before grading, open the Web tab and click
**"Run until 3 months from today"**.
