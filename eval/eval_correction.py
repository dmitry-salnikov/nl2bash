"""
Some manual evaluation correction.
"""

correct_temp_pairs = [
    (
        "Find all .c and .h files in the current directory tree and search them for \"expr\"\n",
        "find -name Pattern File | xargs grep -r Pattern"
    ),
    (
        "Search the current directory tree for files containing \"sh\" in their names\n",
        "find -name Pattern File"
    ),
    (
        "display all the regular files in the folder \"$(FOLDER)\" which are modified in the last $(RETENTION)*24 hours and excluding hidden files\n",
        "find File -type Unknown -mtime Time ! -name Pattern"
    ),
    (
        "To list the number of directories in the `/usr/share' directory tree\n",
        "find /usr/share -type d | wc -l"
    )]

error_temp_pairs = [
    (
        "find  file which case-insensitive name is too in currect directory\n",
        "find -name Pattern File"
    ),
    (
        "Search directory foo for files containing \"foo/bar\" in their full names\n",
        "find foo -type f -iname foo | grep foo"
    ),
    (
        "display all sqlite files in the current directory along with their timestamp\n",
        "find -name Pattern File"
    ),
    (
        "Find all *.tex regular files under current directory\n",
        "find -type Unknown File"
    ),
    (
        "List root's regular files with permissions 4000\n",
        "find -exec ls -l {} \; -perm Permission -type Unknown File"
    ),
    (
        "list regular file which file name end with 'cache' 'xml' or 'html' in current directory\n",
        "find -name Pattern -type Unknown File"
    )]

correct_str_pairs = [
    (
        "List all empty files in the current directory tree\n",
        "find . -empty"
    )]

error_str_pairs = [
    (
        "find  file which case-insensitive name is too in currect directory\n",
        "find . -iname \"filename\""
    ),
    (
        "search for files with the name \"temp\" in the /usr folder\n",
        "find /usr -name '*.sh'"
    ),
    (
        "Find all the files called FindCommandExamples.txt of owner root\n",
        "find / -user root -name tecmint.txt"
    ),
    (
        "Find all .c and .h files in the current directory tree and search them for \"expr\"\n",
        "find . -name '*.[ch]' | xargs grep -E 'expr'"
    ),
    (
        "Find all *.py files under and below the current directory and search them for \"xrange\"\n",
        "find . -name *.py | xargs grep some_function"
    ),
    (
        "Find all .c and .h files in the current directory tree and search them for \"expr\"\n",
        "find . -name \"*.c\" | xargs grep -E 'expr'"
    ),
    (
        "find all the swap files (files ending with ~) in the current folder and delete them\n",
        "find . -name \"*.sh\" -exec rm -r -f {} \;"
    ),
    (
        "display all files in the current directory excluding those that are present in the directories whose name starts with \"efence\" and do not search in the sub directories\n",
        "find \( -name Pattern -prune -or -name Pattern \) -print File"
    )]