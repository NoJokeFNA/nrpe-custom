"""Present the canonical FAQ as a compact index and readable answer sections."""

import html
import re


def render_faq(content):
    groups = re.split(r'<h2 id="([^"]+)">(.*?)</h2>', content)
    index, answers = [], []
    for offset in range(1, len(groups), 3):
        anchor, title, body = groups[offset:offset + 3]
        questions = re.split(r'<h3 id="([^"]+)">(.*?)</h3>', body)
        links, sections = [], []
        for question in range(1, len(questions), 3):
            question_id, heading, answer = questions[question:question + 3]
            safe_id = html.escape(question_id, quote=True)
            links.append('<li><a data-question="' + safe_id + '" href="#' + safe_id
                         + '">' + heading + '</a></li>')
            sections.append('<section class="faq-question" aria-labelledby="' + safe_id + '">'
                            '<h3 id="' + safe_id + '">' + heading
                            + '<a class="question-link" href="#' + safe_id
                            + '" aria-label="Link to this question">#</a></h3>'
                            + '<div class="faq-answer">' + answer + '</div></section>')
        index.append('<section class="faq-index-group"><h3><a href="#' + anchor + '">'
                     + title + '</a></h3><ul>' + ''.join(links) + '</ul></section>')
        answers.append('<section class="faq-group" aria-labelledby="' + anchor + '">'
                       '<h2 id="' + anchor + '">' + title + '</h2>'
                       + questions[0] + ''.join(sections) + '</section>')
    tools = ('<div class="faq-tools" hidden><label for="faq-filter">Find an answer</label>'
             '<div class="faq-search-row"><input id="faq-filter" type="search" '
             'placeholder="Search services, TLS or builds…" aria-controls="faq-answers" '
             'aria-describedby="faq-count"><button id="faq-clear" type="button" hidden>'
             'Clear search</button></div><p id="faq-count" role="status"></p></div>')
    return (groups[0] + tools + '<nav class="faq-index" aria-label="Questions by topic">'
            + ''.join(index) + '</nav><p id="faq-empty" hidden>No answers match your search. '
            'Try a shorter term, such as “TLS”, or clear the search to browse all questions.</p>'
            '<div id="faq-answers">' + ''.join(answers) + '</div>')
