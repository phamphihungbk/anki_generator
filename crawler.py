import json
import os.path
import pickle
import re
from sys import exit
import time

import requests
from requests.cookies import RequestsCookieJar
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from database import Problem, ProblemTag, Tag, Submission, create_tables, Solution
from utils import destructure, random_wait, do, get

COOKIE_PATH = "./cookies.dat"
GRAPHQL_URL = "https://leetcode.com/graphql"

class LeetCodeCrawler:
    def __init__(self):
        # create an http session
        self.session = requests.Session()
        self.browser = webdriver.Chrome(service=webdriver.ChromeService(executable_path="./driver/chromedriver"))
        self.session.headers.update(
            {
                'Host': 'leetcode.com',
                'Cache-Control': 'max-age=0',
                'Upgrade-Insecure-Requests': '1',
                'Referer': 'https://leetcode.com/accounts/login/',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
                'Connection': 'keep-alive'
            }
        )

    def login(self):
        browser_cookies = {}
        if os.path.isfile(COOKIE_PATH):
            with open(COOKIE_PATH, 'rb') as f:
                browser_cookies = pickle.load(f)
        else:
            print("😎 Starting browser login..., please fill the login form")
            try:
                # browser login
                login_url = "https://leetcode.com/accounts/login"
                self.browser.get(login_url)

                WebDriverWait(self.browser, 24 * 60 * 3600).until(
                    lambda driver: driver.current_url.find("login") < 0
                )

                # Wait for user to complete 2FA manually
                time.sleep(10)

                browser_cookies = self.browser.get_cookies()
                with open(COOKIE_PATH, 'wb') as f:
                    pickle.dump(browser_cookies, f)
                print("🎉 Login successfully")

            except Exception as e:
                print(f"🤔 Login Failed: {e}, please try again")
                exit()

        cookies = RequestsCookieJar()
        for item in browser_cookies:
            cookies.set(item['name'], item['value'])

            if item['name'] == 'csrftoken':
                self.session.headers.update({
                    "x-csrftoken": item['value']
                })

        self.session.cookies.update(cookies)

    def fetch_accepted_problems(self):    
        response = self.session.get("https://leetcode.com/api/problems/all/")
        all_problems = json.loads(response.content.decode('utf-8'))
        # filter AC problems
        counter = 0
        for item in all_problems['stat_status_pairs']:
            if item['status'] == 'ac':
                id, slug = destructure(item['stat'], "question_id", "question__title_slug")

                if slug != 'permutation-in-string':
                    continue

                # only update problem if not exists
                if Problem.get_or_none(Problem.id == id) is None:
                    counter += 1
                    # fetch problem
                    do(self.fetch_problem, args=[slug, True])
                    # fetch solution
                    do(self.fetch_solution, args=[slug])
                    
                # always try to update submission
                do(self.fetch_submission, args=[slug])
        print(f"🤖 Updated {counter} problems")

    def fetch_problem(self, slug: str, accepted: bool=False) -> None:
        print(f"🤖 Fetching problem: https://leetcode.com/problem/{slug}/...")
        
        query_params = {
            'operationName': "getQuestionDetail",
            'variables': {'titleSlug': slug},
            'query': '''query getQuestionDetail($titleSlug: String!) {
                        question(titleSlug: $titleSlug) {
                            questionId
                            questionFrontendId
                            questionTitle
                            questionTitleSlug
                            content
                            difficulty
                            stats
                            similarQuestions
                            categoryTitle
                            topicTags {
                            name
                            slug
                        }
                    }
                }'''
        }

        response = self.session.post(
            GRAPHQL_URL,
            data=json.dumps(query_params).encode('utf8'),
            headers={"content-type": "application/json"})
        
        body = json.loads(response.content)

        # parse data
        question = get(body, 'data.question')

        Problem.replace(
            id=question['questionId'], 
            display_id=question['questionFrontendId'],
            title=question["questionTitle"],
            level=question["difficulty"], 
            slug=slug, 
            description=question['content'],
            accepted=accepted,
            approaches='',
            mistakes='',
            edgecases='',
            clarify_questions='',
            note='',
        ).execute()

        for item in question['topicTags']:
            if Tag.get_or_none(Tag.slug == item['slug']) is None:
                Tag.replace(
                    name=item['name'],
                    slug=item['slug']
                ).execute()

            ProblemTag.replace(
                problem=question['questionId'],
                tag=item['slug']
            ).execute()
        
        random_wait(10, 15)

    def fetch_solution(self, slug: str) -> None:
        print(f"🤖 Fetching solution for problem: {slug}")
        
        query_params = {
            "operationName": "QuestionNote",
            "variables": {"titleSlug": slug},
            "query": '''
            query QuestionNote($titleSlug: String!) {
                question(titleSlug: $titleSlug) {
                    questionId
                    article
                    note
                    solution {
                      id
                      content
                      contentTypeId
                      canSeeDetail
                      paidOnly
                      rating {
                        id
                        count
                        average
                        userRating {
                          score
                          __typename
                        }
                        __typename
                      }
                      __typename
                    }
                    __typename
                }
            }
            '''
        }

        response = self.session.post(GRAPHQL_URL,
            data=json.dumps(query_params).encode('utf8'),
            headers={"content-type": "application/json"},
        )
        
        body = json.loads(response.content)

        # parse data
        solution = get(body, "data.question")
        is_solution_existed = solution['solution'] is not None and solution['solution']['paidOnly'] is False
        
        if is_solution_existed:
            data = self.decompose_note(solution['note'])
            print(data)
            Problem.update({
                 Problem.approaches:data['approaches'],
                 Problem.mistakes:data['mistakes'],
                 Problem.edgecases:data['edgecases'],
                 Problem.clarify_questions:data['clarify_questions'],
                 Problem.note:data['note'],
            }).where(Problem.slug == slug).execute()
            
            Solution.replace(
                problem=solution['questionId'],
                url=f"https://leetcode.com/articles/{slug}/",
                content=solution['solution']['content']
            ).execute()
        
        random_wait(10, 15)


    def decompose_note(self, input_str: str) -> dict:
        """
        Extracts sections (clarify questions, edgecases, approaches, mistakes, note) from the input string.

        :param input_str: The input string with section headers and content.
        :return: Dictionary with extracted content for each section.
        """

        # Improved regex pattern to capture content between section headers
        pattern = re.compile(
            r"clarify questions:\s*(?P<clarify>(?:- .*(?:\n|$))*)"      # Clarify Questions
            r"(?:\nedgecases:\s*(?P<edgecase>(?:- .*(?:\n|$))*)?)?"     # Edgecases (optional)
            r"(?:\napproaches:\s*(?P<approach>(?:- .*(?:\n|$))*)?)?"    # Approaches (optional)
            r"(?:\nmistakes:\s*(?P<mistake>(?:- .*(?:\n|$))*)?)?"       # Mistakes (optional)
            r"(?:\nnote:\s*(?P<note>.*))?",                             # Note (optional)
            re.IGNORECASE
        )

        match = pattern.search(input_str)
        if not match:
            print("❌ No matches found. Check section headers and formatting.")
            return {section: "None" for section in ["clarify_questions", "edgecases", "approaches", "mistakes", "note"]}

        def format_title(key: str) -> str:
            """Converts keys like 'clarify_questions' to 'Clarify Questions'."""
            return key.replace("_", " ").title()

        def format_section(title: str, text: str, is_bullet_section: bool = True) -> str:
            """
            Formats a section into a human-readable string.

            :param title: Section title.
            :param text: Section content.
            :param is_bullet_section: True if the section contains bullet points; False otherwise.
            :return: Formatted section string.
            """
            if not text:
                return f"{title}:\n  - None" if is_bullet_section else f"{title}:\nNone"

            lines = [line.strip('- ').strip() for line in text.strip().split('\n') if line.strip()]
            if is_bullet_section:
                return f"{title}:\n" + "\n".join(f"  - {line}" for line in lines)
            else:
                return f"{title}:\n{lines[0]}"  # For single-line content like 'note'
        
        # Extract, clean, and format sections
        sections = {
            "clarify_questions": format_section(format_title("🔹 clarify_questions"), match.group('clarify')),
            "edgecases": format_section(format_title("🔹 edge_cases"), match.group('edgecase')),
            "approaches": format_section(format_title("🔹 approaches"), match.group('approach'), is_bullet_section=False),
            "mistakes": format_section(format_title("🔹 mistakes"), match.group('mistake')),
            "note": format_section(format_title("🔹 note"), match.group('note'), is_bullet_section=False),
        }

        return sections
    
        """
        Transforms decomposed notes into individually formatted strings for each attribute.
        
        :param decomposed_notes: Dictionary with keys: clarify_questions, edgecases, approaches, mistakes, note.
        :return: Dictionary with formatted strings for each attribute.
        """

        def format_list_section(title: str, items: list) -> str:
            """Formats a list into bullet points with a title."""
            if not items:
                return f"{title}:\n  - None"
            formatted_items = "\n".join(f"  - {item}" for item in items)
            return f"{title}:\n{formatted_items}"

        def format_text_section(title: str, content: str) -> str:
            """Formats text sections with a title."""
            return f"{title}:\n{content.strip() or 'None'}"

        return {
            "clarify_questions": format_list_section("Clarify_questions", decomposed_notes["clarify_questions"]),
            "edgecases": format_list_section("Edgecases", decomposed_notes["edgecases"]),
            "approaches": format_text_section("Approaches", decomposed_notes["approaches"]),
            "mistakes": format_list_section("Mistakes", decomposed_notes["mistakes"]),
            "note": format_text_section("Note", decomposed_notes["note"])
        }

    def fetch_submission(self, slug: str) -> None:
        print(f"🖍 Fetching submission for problem: {slug}")
        
        query_params = {
            'operationName': "Submissions",
            'variables': {
                "offset": 0, 
                "limit": 20, 
                "lastKey": '', 
                "questionSlug": slug
            },
            'query': '''query Submissions($offset: Int!, $limit: Int!, $lastKey: String, $questionSlug: String!) {
                submissionList(offset: $offset, limit: $limit, lastKey: $lastKey, questionSlug: $questionSlug) {
                    lastKey
                    hasNext
                    submissions {
                        id
                        statusDisplay
                        lang
                        runtime
                        timestamp
                        url
                        isPending
                        __typename
                    }
                    __typename
                }
            }'''
        }
        
        response = self.session.post(
            GRAPHQL_URL,
            data=json.dumps(query_params).encode('utf8'),
            headers={"content-type": "application/json"},
        )

        body = json.loads(response.content)

        # parse data
        submissions = get(body, "data.submissionList.submissions")
        if len(submissions) > 0:
            for sub in submissions:
                if Submission.get_or_none(Submission.id == sub['id']) is not None:
                    continue

                if sub['statusDisplay'] == 'Accepted':
                    url = sub['url']
                    self.browser.get(f'https://leetcode.com{url}')
                    element = WebDriverWait(self.browser, 10).until(
                        EC.presence_of_element_located((By.ID, "result_date"))  # Replace "someId" with the ID of the actual element you are waiting for
                    )
                    html = self.browser.page_source
                    pattern = re.compile(
                        r'submissionCode: \'(?P<code>.*)\',\n  editCodeUrl', re.S
                    )
                    matched = pattern.search(html)
                    code = matched.groupdict().get('code') if matched else None
                    if code:
                        Submission.insert(
                            id=sub['id'],
                            slug=slug,
                            language=sub['lang'],
                            created=sub['timestamp'],
                            source=code.encode('utf-8')
                        ).execute()
                    else:
                        raise Exception(f"Cannot get submission code for problem: {slug}")
        
        random_wait(10, 15)


if __name__ == '__main__':
    create_tables()
    crawler = LeetCodeCrawler()
    crawler.login()
    crawler.fetch_accepted_problems()
