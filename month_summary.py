#!/opt/readwise/venv/bin/python

import requests
import datetime
import urllib3
from getpass import getpass
import pprint
from bs4 import BeautifulSoup
from openai import OpenAI
import openai
import re
import datetime
import smtplib
import re
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from notion_client import Client
import os
import json
import calendar


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG_PATH = "/etc/scrt/api_key"

def load_api_keys(config_path):
	"""
	Load API keys from a JSON configuration file.
	"""
	try:
		with open(config_path, "r") as file:
			data = json.load(file)
		return data
	except FileNotFoundError:
		print(f"Erreur : Le fichier {config_path} n'existe pas.")
		return None
	except json.JSONDecodeError:
		print("Erreur : Le fichier JSON est mal formaté.")
		return None
# Load API keys
api_keys = load_api_keys(CONFIG_PATH)
# Check and assign the variables if the file was loaded successfully
if api_keys:
	DATABASE_ID = api_keys.get("NOTION_DATABASE_ID")	
	NOTION_API_KEY = api_keys.get("NOTION_TOKEN")
	SENDER_MAIL = api_keys.get("SENDER_MAIL")
	RECIPIENT_MAIL_SECU = api_keys.get("RECIPIENT_MAIL_SECU")
	RECIPIENT_MAIL = api_keys.get("RECIPIENT_MAIL")
	PWD_MAIL = api_keys.get("PWD_MAIL")
	print("Clés chargées avec succès !")

BASE_URL = 'https://readwise.io/api/v2'


# Headers for Notion API
headers = {
	"Authorization": f"Bearer {NOTION_API_KEY}",
	"Content-Type": "application/json",
	"Notion-Version": "2022-06-28"
}

def get_last_month_date_range():
	"""
	Returns the first and last date of the previous month.
	"""
	today = datetime.date.today()
	first_day_last_month = today.replace(day=1) - datetime.timedelta(days=1)
	first_day_last_month = first_day_last_month.replace(day=1)
	last_day_last_month = today.replace(day=1) - datetime.timedelta(days=1)
	
	return first_day_last_month.isoformat(), last_day_last_month.isoformat()

def query_notion_database():
	"""
	Queries Notion database for articles published last month
	with a "HoF" checkbox checked and specific tags.
	"""
	start_date, end_date = get_last_month_date_range()
	query = {
		"filter": {
			"and": [
				{
					"property": "Publication Date",
					"date": {
						"on_or_after": start_date
					}
				},
				{
					"property": "Publication Date",
					"date": {
						"on_or_before": end_date
					}
				},
				{
					"property": "HoF",
					"checkbox": {
						"equals": True
					}
				},
				{
					"or": [
						{
							"property": "Tag",
							"multi_select": {
								"contains": "Cybersecurite"
							}
						},
						{
							"property": "Tag",
							"multi_select": {
								"contains": "Informatique"
							}
						}
					]
				}
			]
		}
	}
	
	url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
	response = requests.post(url, headers=headers, json=query)
	
	if response.status_code == 200:
		return response.json().get("results", [])
	else:
		print(f"Erreur API Notion: {response.status_code} - {response.text}")
		return []

def generate_email_content(articles):
	"""
	Generates the email body content from the retrieved Notion articles.
	"""
	email_body = []
	for article in articles:
		title = article.get("properties", {}).get("Title", {}).get("title", [{}])[0].get("text", {}).get("content", "Sans titre")
		date = article.get("properties", {}).get("Publication Date", {}).get("date", {}).get("start", "Inconnue")
		url = article.get("properties", {}).get("Article URL", {}).get("url", "")
		source = article.get("properties", {}).get("Source", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "Inconnu")
		summary = article.get("properties", {}).get("Summary", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "Pas de résumé")
		
		source_link = f'<a href="{url}">{source}</a>'
		email_body.append(f"""
			<h4>{title}</h4>					
			<p>{summary}</p>
			<p><strong> {date} / {source_link}</strong></p>
			<hr/>
		""")
	
	return "".join(email_body)

def get_last_month_name_and_year():
	"""
	Retrieves the name and year of the last month.
	"""
	today = datetime.date.today()
	first_day_last_month = today.replace(day=1) - datetime.timedelta(days=1)
	month_name = calendar.month_name[first_day_last_month.month]
	year = first_day_last_month.year
	return month_name, year

def send_html_email(to_email, object, html_body):
	"""
	Sends an HTML formatted email with the specified content.
	"""
	from_email = SENDER_MAIL
	password = PWD_MAIL 

	msg = MIMEMultipart("alternative")
	msg["Subject"] = object
	msg["From"] = from_email
	msg["To"] = to_email

	text_body = "Votre client mail ne supporte pas l'affichage HTML."
	part_text = MIMEText(text_body, "plain", "utf-8")
	msg.attach(part_text)
	part_html = MIMEText(html_body, "html", "utf-8")
	msg.attach(part_html)
	context = ssl.create_default_context()
	with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
		server.login(from_email, password)
		server.sendmail(from_email, to_email, msg.as_string())

def main():
	"""
	Main function to query Notion, format the email content,
	and send a summary of articles from last month.
	"""
	articles = query_notion_database()
	
	if not articles:
		print("Aucun article trouvé pour le mois dernier.")
		email_content="Pas d'articles en base pour le mois dernier."
	else:
		email_content = generate_email_content(articles)
	#print(email_content)  # À envoyer via un service d'email
	month_name, year = get_last_month_name_and_year()
	subject = f"Récapitulatif des articles CyberSecurite du mois de {month_name} {year}"
	send_html_email(
		to_email=RECIPIENT_MAIL_SECU,
		object=subject,
		html_body=email_content
	)

if __name__ == "__main__":
	main()
