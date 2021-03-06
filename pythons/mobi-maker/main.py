# 1. [Done] Test kindlegen executable.
#    - TOC.
#    - Chapter.
#    - Line-break.
#    - `zip -r TestKindleBook.epub TestKindleBook`.
#    - `/var/local/app-binaries/kindlegen-2.9/kindlegen TestKindleBook.epub`.
# 2. Read file line by line.
# 3. Parse line with regex.
# 4. Prepare HTML template.
# 5. Write HTML with parse result and template.
# 6. Use kindlegen to make mobi file.
import re
import os
import time

_TEMPLATE_START = (
    '<html lang="zh">'
    '<head><title>%s</title>'
    '<meta http-equiv="content-type" content="text/html; charset=UTF-8">'
    '<style>h1{font-size:1em;font-weight:200;}</style>'
    '</head><body style="background-color:#CCE8CF;">'
)
_TEMPLATE_END = '</body></html>'

_CHAPTER_TITLE_PATTERNS = [
    r'^\#+(第.+章\s?[^\#]+)\#+\s*$',
    r'^\s?(第.+章\s?.+)\s*$',
    r'^卷\s+(第.+章\s?.+)\s*$',
    r'^\s?(\d+[、，]\s?.+)\s*$',
]


def _search_chapter_name(line):
    for pattern in _CHAPTER_TITLE_PATTERNS:
        search_result = re.search(pattern, line)
        if search_result is not None:
            return search_result
    return None


def _get_arguments():
    import argparse
    parser = argparse.ArgumentParser(description='Parse file name.')
    parser.add_argument(
        '--encoding', '-c', type=str, default='UTF-8',
        help='The encoding of the given files. Support GB2312, UTF-8 and GBK',
    )
    parser.add_argument(
        'file_names', metavar='file_name', type=str,
        nargs='+', help='file name',
    )
    return parser.parse_args()


def _process_file(file_name, encoding):
    with open(file_name, 'r', encoding=encoding) as file:
        lines_limit = 1000000

        processed_lines_count = 0
        chapters_count = 0
        words_count = 0
        line = file.readline()
        head_and_toc = [
            _TEMPLATE_START % line[:-1],
            '<h1 id="content">目录</h1>',
        ]
        line = file.readline()
        text = []

        while line and (processed_lines_count < lines_limit):
            line_len = len(line)
            if 1 == line_len:
                line = file.readline()
                continue
            search_result = _search_chapter_name(line)
            if search_result is not None:
                chapters_count += 1
                chapter_name = search_result.group(1)
                chapter_id = 'c{}'.format(chapters_count)
                head_and_toc.append('<p><a href="#{}">{}</a></p>'.format(chapter_id, chapter_name))
                text.append('<h1 id="{}">{}</h1>'.format(chapter_id, chapter_name))
                text.append('<p><a href="#content">回目录</a>'
                            '| | | |<a href="#c{}">上一章</a>'
                            '| | | |<a href="#c{}">下一章</a></p>'.format(chapters_count - 1, chapters_count + 1))
            else:
                words_count += line_len
                text.append('<p>{}</p>'.format(line[:-1]))
            processed_lines_count += 1
            line = file.readline()
        print(
            'Processed:', file_name,
            ', chapters count:', chapters_count,
            ', lines count:', processed_lines_count,
            ', words count:', words_count,
        )
        return head_and_toc, text


def _save_to_html(file_name, head_and_toc, text):
    with open(file_name, 'w+', encoding='UTF-8') as file:
        file.writelines(head_and_toc)
        file.writelines(text)
        file.writelines([_TEMPLATE_END])


def _make():
    start_time = time.time()
    arguments = _get_arguments()
    encoding = arguments.encoding
    file_names = arguments.file_names
    for file_name in file_names:
        if not file_name.endswith('.txt'):
            print('Invalid file type. Expected "*.txt" files.')
            continue
        toc, text = _process_file(file_name, encoding)
        html_name = '{}.html'.format(file_name[:-4])
        _save_to_html(html_name, toc, text)
        os.system('/var/local/app-binaries/kindlegen-2.9/kindlegen {}'.format(
            html_name,
        ))
    print('Totally cost {:.4f} seconds.'.format(time.time() - start_time))


if __name__ == '__main__':
    _make()
