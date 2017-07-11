#!/usr/bin/env python3

import MySQLdb # sudo apt install libmysqlclient-dev python-dev && pip3 install mysqlclient
import requests # pip3 install requests
import unittest
import hashlib
from path import Path # pip3 install path.py

DEFAULT_PATH = "/blogpost1/"
DEFAULT_SITE = "petersworld.com"
INVALID_QUERY_PARAMS = "Please submit both query parameters 'site' and 'path'"
COMMENT_SIDECAR_URL = 'http://localhost/comment-sidecar.php'

class PlaylistTest(unittest.TestCase):
    def setUp(self):
        # first, run `docker-compose up`
        db = MySQLdb.connect(host='127.0.0.1', port=3306, user='root', passwd='root', db='comment-sidecar')
        cur = db.cursor()
        with Path("create-comments-table.sql").open('r') as sql:
            query = "\n".join(sql.readlines())
            cur.execute(query)

    def test_GET_missing_query_params(self):
        response = requests.get(COMMENT_SIDECAR_URL)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], INVALID_QUERY_PARAMS)

    def test_GET_empty_query_params(self):
        response = get_comments(site='', path='')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], INVALID_QUERY_PARAMS)

    def test_GET_missing_path(self):
        response = get_comments(site='domain.com', path='')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], INVALID_QUERY_PARAMS)

    def test_GET_missing_site(self):
        response = get_comments(site='', path='blogpost1')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], INVALID_QUERY_PARAMS)

    def test_GET_empty_array_if_no_comments(self):
        response = get_comments()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, '[]')

    def test_POST_and_GET_comment(self):
        post_payload = create_payload()
        post_response = requests.post(url=COMMENT_SIDECAR_URL, json=post_payload)
        self.assertEqual(post_response.status_code, 201)
        self.assertEqual(post_response.text, "")

        get_response = get_comments()
        self.assertEqual(get_response.status_code, 200)
        comments_json = get_response.json()
        self.assertEqual(len(comments_json), 1)

        returned_comment = comments_json[0]
        self.assertEqual(returned_comment["author"], post_payload["author"])
        self.assertEqual(returned_comment["content"], post_payload["content"])
        self.assertEqual(returned_comment["creationTimestamp"], post_payload["creationTimestamp"])
        gravatar_url = create_gravatar_url(post_payload["email"])
        self.assertEqual(returned_comment["gravatarUrl"], gravatar_url)
        self.assertTrue('email' not in returned_comment, "Don't send the email back to browser")
        self.assertTrue('id' not in returned_comment, "Don't send the id to browser")
        self.assertTrue('path' not in returned_comment, "Don't send the path to browser")
        self.assertTrue('site' not in returned_comment, "Don't send the site to browser")
        self.assertTrue('replyTo' not in returned_comment, "Don't send the replyTo to browser")

    def test_GET_different_paths(self):
        path_with_two_comments = "/post1/"
        path_with_one_comment = "/post2/"

        post_payload = create_payload()
        post_payload['path'] = path_with_two_comments
        requests.post(url=COMMENT_SIDECAR_URL, json=post_payload)
        requests.post(url=COMMENT_SIDECAR_URL, json=post_payload)
        post_payload['path'] = path_with_one_comment
        requests.post(url=COMMENT_SIDECAR_URL, json=post_payload)

        response = get_comments(path=path_with_two_comments)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

        response = get_comments(path=path_with_one_comment)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_GET_different_sites(self):
        site_with_two_comments = "mydomain2.com"
        site_with_one_comment = "mydomain1.com"

        post_payload = create_payload()
        post_payload['site'] = site_with_two_comments
        requests.post(url=COMMENT_SIDECAR_URL, json=post_payload)
        requests.post(url=COMMENT_SIDECAR_URL, json=post_payload)
        post_payload['site'] = site_with_one_comment
        requests.post(url=COMMENT_SIDECAR_URL, json=post_payload)

        response = get_comments(site=site_with_two_comments)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

        response = get_comments(site=site_with_one_comment)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)


def get_comments(site: str = DEFAULT_SITE, path: str = DEFAULT_PATH):
    return requests.get("{}?site={}&path={}".format(COMMENT_SIDECAR_URL, site, path))

def create_payload():
    return {
        "author": "Peter",
        "content": "Peter's comment",
        "creationTimestamp": "1499604757",
        "email": "peter@petersworld.com",
        "path": DEFAULT_PATH,
        "replyTo": None,
        "site": DEFAULT_SITE
    }

def create_gravatar_url(email: str) -> str:
    md5 = hashlib.md5()
    md5.update(email.strip().lower().encode())
    return "https://www.gravatar.com/avatar/" + md5.hexdigest()

if __name__ == '__main__':
    unittest.main()
