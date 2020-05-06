#!python3
import logging
import tempfile
from pathlib import Path
from argparse import ArgumentParser
from collections import defaultdict, OrderedDict
from itertools import chain
import openpyxl
import requests


logger = logging.getLogger(__name__)


prsr = ArgumentParser(
    prog="freespringer",
    description="Download multiple free Springer books at once."
    )
prsr.add_argument(
    "-a", "--available-packages", action='store_true',
    help="Print list of available packages (general topics) and its "
         "identifiers and terminate."
)
prsr.add_argument(
    "-s", "--available-subjects", type=int, nargs='*', metavar="ID",
    help="Print list of available subjects from given packages with its "
         "identifiers and terminate."
)
prsr.add_argument(
    "-A", "--available-topics", action='store_true',
    help="Print list of all available topics (pacakges and subjects) and its "
         "identifiers and terminate."
)
prsr.add_argument(
    "-b", "--subjects-books", type=int, nargs='*', metavar="ID",
    help="Print list of book titles in given subjects and terminate."
)
prsr.add_argument(
    "-B", "--packages-books", type=int, nargs='*', metavar="ID",
    help="Print list of book titles in given pacakges and terminate."
)
prsr.add_argument(
    "-p", "--pdf", type=int, nargs='*', metavar="ID", default=tuple(),
    help="Download books regarding specified topics in .pdf format. "
         "Expects list of topics' identifiers as argunets."
)
prsr.add_argument(
    '-e', '--epub', type=int, nargs='*', metavar="ID", default=tuple(),
    help="Download books regarding specified topics in .epub format. "
         "Expects list of topics' identifiers as argunets. "
         "Please note, that automated access to these resources is against "
         "Springer's terms of use. Proceed on your own responsibility."
)
prsr.add_argument(
    '-d', '--destination', type=Path, metavar="PATH", default=Path(),
    help='Destination directory. Defaults to current working directory.'
)
prsr.add_argument(
    "-g", "--group", action='store_true',
    help="Save downloaded files in subdirectories corresponding to book's "
         "packages rather than directly do destination directory."
)
prsr.add_argument(
    "-F", "--force_download", action='store_true',
    help="Download list of available books from Springer rather than using "
         "cached version."
)
verbosity = prsr.add_mutually_exclusive_group()
verbosity.add_argument(
    '--verbose', action='store_true',
    help='Print more informations to stdout.'
)
verbosity.add_argument(
    '--debug', action='store_true',
    help='Print debug logs to stdout.'
)
verbosity.add_argument(
    '--silent', action='store_true',
    help='Only errors are displayed.'
)


TMPFILE = Path(tempfile.gettempdir()).joinpath("getspringercache", "books.xlsx")


BOOKS_TITLES = {}  # {doi: title}
BOOKS_PACKAGES = {}
IDS_OF_PACKAGES = OrderedDict()  # {package: id}
IDS_OF_SUBJECTS = OrderedDict()  # {subject: id}
TOPICS_BOOKS = defaultdict(list)  # {id: [list of dois]}
TOPICS_IDS = OrderedDict()  # {id: topic}
PACKAGES_RELS = defaultdict(set)  # {package: {set of subjects}}
SUBJECTS_RELS = defaultdict(set)  # {subject: {set of packages}}
LONGEST = 50  # longest topic name


def setup_globals(force_download):
    logger.debug("Setting up global variables.")
    global BOOKS_TITLES, TOPICS_BOOKS, TOPICS_IDS, PACKAGES_RELS, SUBJECTS_RELS
    global BOOKS_PACKAGES, IDS_OF_PACKAGES, IDS_OF_SUBJECTS, LONGEST
    PACKAGES_BOOKS = defaultdict(list)  # {package: [list of dois]}
    SUBJECTS_BOOKS = defaultdict(list)  # {subject: [list of dois]}
    books = get_raw_list_of_books(force_download)
    for title, package, subjects, doi in books:
        subjects = [subj.strip() for subj in subjects.split(';')]
        subjects = [subj if len(subj) < LONGEST else subj[:LONGEST-3]+"..." for subj in subjects]
        PACKAGES_BOOKS[package].append(doi)
        BOOKS_PACKAGES[doi] = package
        for subj in subjects:
            SUBJECTS_BOOKS[subj].append(doi)
            PACKAGES_RELS[package].add(subj)
            SUBJECTS_RELS[subj].add(package)
        BOOKS_TITLES[doi] = title
    for id, topic in enumerate(sorted(PACKAGES_RELS.keys()), start=1):
        IDS_OF_PACKAGES[topic] = id
        TOPICS_IDS[id] = topic
    for id, topic in enumerate(sorted(SUBJECTS_RELS.keys()), start=1+len(PACKAGES_RELS)):
        IDS_OF_SUBJECTS[topic] = id
        TOPICS_IDS[id] = topic
    for topic, books in PACKAGES_BOOKS.items():
        TOPICS_BOOKS[IDS_OF_PACKAGES[topic]] = books
    for topic, books in SUBJECTS_BOOKS.items():
        TOPICS_BOOKS[IDS_OF_SUBJECTS[topic]] = books
    logger.debug("Script ready to operate.")
    # LONGEST = max(map(len, SUBJECTS_RELS.keys()))


def _download_books_list():
    """Get list of free springer books from web."""
    logger.debug("Fetching list of books from Springer site.")
    link = "https://resource-cms.springernature.com/springer-cms/rest/v1/content/17858272/data/v5"
    resp = requests.get(link, stream=True)
    logger.debug(f"Response status code: {resp.status_code}.")
    if not resp.status_code == 200:
        raise RuntimeError(
            f"Cannot get list of books from web "
            f"(response status code: {resp.status_code})."
        )
    TMPFILE.parent.mkdir(parents=True, exist_ok=True)
    with TMPFILE.open("wb") as handle:
        for chunk in resp.iter_content(chunk_size=128):
            handle.write(chunk)
    logger.debug(f"Fetched xmlx stored in temporary file {handle.name}.")    


def get_raw_list_of_books(force_download):
    if force_download or not TMPFILE.exists():
        _download_books_list()
    else:
        logger.debug("Using cached version of books list.")
    with TMPFILE.open("rb") as handle:
        wb = openpyxl.load_workbook(handle)
        sheet = wb.active
        titles = (c.value for c in sheet['A'])
        packages = (c.value for c in sheet['L'])
        subjects = (c.value for c in sheet['T'])
        doinrs = (c.value.strip("http://doi.org/") for c in sheet['R'])
        iterator = zip(titles, packages, subjects, doinrs)
        headers = next(iterator)
        books = list(iterator)
    logger.info("List of free Springer books loaded.")
    return books


def print_available_topics():
    print_available_packages()
    print_available_subjects()


def print_available_packages():
    print("\nList of available packages:\n")
    print(f" ID   {'PACKAGE NAME': <{LONGEST}}   BOOKS")
    print('   ' + "-" * (13 + LONGEST))
    for pckg, idx in IDS_OF_PACKAGES.items():
        print(f"{idx: >5}   {pckg: <{LONGEST}}   {len(TOPICS_BOOKS[idx]): >5}")
        
        
def print_available_subjects(pckg_ids=None):
    pckg_ids = set(pckg_ids) if pckg_ids else IDS_OF_PACKAGES.values()
    subjects = {s for pckg, subs in PACKAGES_RELS.items() for s in subs if IDS_OF_PACKAGES[pckg] in pckg_ids}
    print("\nList of subjects in requested packages:\n")
    print(f" SUBJ ID   {'SUBJECT NAME': <{LONGEST}}   {'IN PACKAGES': <{20}}BOOKS")
    print(' ' + "-" * (38 + LONGEST))
    for subj in sorted(subjects):
        pacakges = sorted(IDS_OF_PACKAGES[p] for p in SUBJECTS_RELS[subj])
        print(
            f"{IDS_OF_SUBJECTS[subj]: >8}   {subj: <{LONGEST}}   "
            f"{', '.join(map(str, pacakges)): <20}"
            f"{len(TOPICS_BOOKS[IDS_OF_SUBJECTS[subj]]): >5}"
        )
    print('\n')


def print_books_in_topic(subjects, packages):
    subjects = subjects or []
    packages = packages or []
    for idx in packages:
        if not 0 < idx <= len(PACKAGES_RELS):
            print(f"NO PACKAGE WITH ID = {idx}.")
            continue
        print(f"\nBooks in package \"{TOPICS_IDS[idx]}\":")
        for doi in TOPICS_BOOKS[idx]:
            print("   " + BOOKS_TITLES[doi])
    for idx in subjects:
        if not len(PACKAGES_RELS) < idx <= len(SUBJECTS_RELS):
            print(f"NO SUBJECT WITH ID = {idx}.")
            continue
        print(f"\nBooks in subject \"{TOPICS_IDS[idx]}\":")
        for doi in TOPICS_BOOKS[idx]:
            print("   " + BOOKS_TITLES[doi])


LINKS = {
    "pdf": "https://link.springer.com/content/pdf/{doi}.pdf",
    "epub": "https://link.springer.com/download/epub/{doi}.epub",
}


def _download_book(doi: str, dest: Path, ext: str, group: str, already_downloaded: set):
    """Download book in desired format (pdf or epub).
    
    if `group` is an empty string, file will be saved directly do `dest` directory,
    otherwise to subdirectory named `group`"""
    if doi in already_downloaded:
        logger.debug(f"Book {doi} already downloaded in {ext} format, skipping.")
        return
    logger.info(f"Downloading book {doi}.")
    bookname = BOOKS_TITLES[doi]
    escaped = requests.utils.quote(doi, safe='')
    filename = "-".join(bookname.split())
    path = dest.joinpath(group, filename).with_suffix('.' + ext)
    path.parent.mkdir(exist_ok=True)
    link = LINKS[ext].format(doi=escaped)
    resp = requests.get(link, stream=True)
    if not resp.status_code == 200:
        logger.warning(
            f"Couldn't download book '{bookname}' "
            f"(response code: {resp.status_code})."
        )
        return
    with path.open("wb") as handle:
        for chunk in resp.iter_content(chunk_size=128):
            handle.write(chunk)
    logger.info(f"Book {doi} saved.")
    already_downloaded.add(doi)
            
            
def download_books(topics: list, dest: Path, extention: str, group: bool = False):
    try:
        _ = LINKS[extention]
    except KeyError:
        logger.error(f"Unsupported format: '{extention}'.")
        return
    if not BOOKS_TITLES:
        setup_globals()
    logger.info(f"Entering {extention} download section.")
    already_downloaded = set()
    for tid in topics:
        for doi in TOPICS_BOOKS[tid]:
            _download_book(doi, dest, extention, BOOKS_PACKAGES[doi] if group else '', already_downloaded)
    logger.info(f"Downloading books in {extention} format finished.")


if __name__ == "__main__":
    args = prsr.parse_args()
    if args.debug:
        level = logging.DEBUG
    elif args.verbose:
        level = logging.INFO
    elif args.silent:
        level = logging.ERROR
    else:
        level = logging.WARNING
    logging.basicConfig(level=level)
    setup_globals(args.force_download)
    if args.available_topics or (args.available_packages and args.available_subjects):
        print_available_topics()
    elif args.available_packages:
        print_available_packages()
    elif args.available_subjects:
        print_available_subjects(args.available_subjects)
    elif args.subjects_books or args.packages_books:
        print_books_in_topic(args.subjects_books, args.packages_books)
    else:
        num_pdfs, num_epubs = map(
            len, ({b for t in topics for b in TOPICS_BOOKS[t]} for topics in (args.pdf, args.epub))
        )
        details = [f"{num_pdfs} pdfs" if num_pdfs else '', f"{num_epubs} epubs" if num_epubs else '']
        details = ' and '.join([d for d in details if d])
        logger.info(f"{num_pdfs + num_epubs} files will be downloaded from the Springer site ({details}).")
        if args.pdf:
            download_books(args.pdf, args.destination, "pdf", args.group)
        if args.epub:
            download_books(args.epub, args.destination, "epub", args.group)
