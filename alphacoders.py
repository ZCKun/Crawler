import requests
from bs4 import BeautifulSoup
import sys

# <span class='btn btn-success btn-custom download-button' data-id="969135" data-type="jpg" data-server="images5" data-user-id="142016">

headers = {
	"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
	"Host": "wall.alphacoders.com",
	"Origin": "https://wall.alphacoders.com",
}

home_url = "https://wall.alphacoders.com/"


def getDownLink(wallpaper_id, _type, server, user_id):
	url = "https://wall.alphacoders.com/get_download_link.php"
	data = {
		"wallpaper_id": wallpaper_id,
		"type": _type,
		"server": server,
		"user_id": user_id,
	}

	resp = requests.post(url, data=data, headers=headers)
	if resp.status_code != 200:
		print("get download link failed.")
		sys.exit()

	return resp.text

def parse(body):
	soup = BeautifulSoup(body, "html.parser")
	containers = soup.findAll("div", attrs={"class":"thumb-container-big"})

	hrefs = []

	for container in containers:
		href = container.find("div", attrs={"class":"boxgrid"}).find("a").get('href')
		hrefs.append(home_url + href)

	if len(hrefs) > 0:
		return hrefs
	return None


def alphacoders(page):
	url = "https://wall.alphacoders.com/search.php?search=girl&page={}".format(page)
	resp = requests.get(url, headers=headers)
	if resp.status_code != 200:
		print("request error.")
		sys.exit()
	hrefs = parse(resp.text)
	if hrefs == None:
		sys.exit()
#<span class='btn btn-success btn-custom download-button' data-id="969135" data-type="jpg" data-server="images5" data-user-id="142016">
	for href in hrefs:
		resp2 = requests.get(href, headers=headers)

		soup = BeautifulSoup(resp2.text, "html.parser")
		dwnbtn = soup.find("span", attrs={"class":"download-button"})
		data_id = dwnbtn.get('data-id')
		data_type = dwnbtn.get('data-type')
		data_server = dwnbtn.get('data-server')
		data_user_id= dwnbtn.get('data-user-id')

		link = getDownLink(data_id, data_type, data_server, data_user_id)
		print(link)


if __name__ == "__main__":
	alphacoders(1)
