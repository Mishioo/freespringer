# freespringer
At once download multiple books given by Springer for free.

As was reported [here](
https://www.springernature.com/gp/librarians/news-events/all-news-articles/industry-news-initiatives/free-access-to-textbooks-for-institutions-affected-by-coronaviru/17855960
)
Springer have opened access to a number of essential textbooks from all disciplines (over 300 in english) in aid to support learning and teaching at higher education institutions worldwide during Coronavirus pandemic.
The list of books, however, is available in a form not very convinient to browse (xlsx file), and downloading multiple files is quite cumbersome.
Therefore I decided to write this small Python script to help me browse and download these files.
I'm sharing it, because maybe it will now help also someone else, who is - like me - starving for knowledge but too lazy to click many buttons. ;)

## geting started

- Install Python (version at least 3.6) if you do not have it in your system.
- Clone or download this repository.
- Install `openpyxl` and `requests` (or simply run `python -m pip install -r ./requirements.txt`).
- You're ready to go!

## how to use

Run from command line:
- `python -m freespringer -a` to see available packages (general topics) with their IDs
- `python -m freespringer -s ID` to see what subjects a package contains
- `python -m freespringer -b ID` to see what books a subject contains
- `python -m freespringer -p ID` to download books about a subject or topic
- `python -m freespringer --help` to see more detailed documentation

### requirements

```
Python 3.6+
openpyxl
requests
```


