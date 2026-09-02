# Quotables
A Corpus of Quotes.

# Quotable Quote

*"I fear not the man who has practiced 10,000 kicks once, but I fear the man who has practiced one kick 10,000 times."*
**Bruce Lee**

# Statistics:
 - 39,269 quotes with
 - 1,015,338 words from
 - 3,112 people
 - 732 quotes carry a verified first-hand source (see docs/SOURCING.md)

# Format
`author-quote.txt` is tab-separated with three columns:

1. author
2. quote
3. sources: a JSON list of strings naming the first-hand work the quote comes from
   (book, essay, poem, play with act/scene, speech, letter, interview), e.g.
   `["The Tragedy of Macbeth, Act 1, Scene 7"]`. It is `[]` when no first-hand source has
   been verified yet, or when the quote is a known misattribution. The author's name is not
   repeated inside the string.

How the sources were found, what evidence backs each one, and how to extend the column are
described in [docs/SOURCING.md](docs/SOURCING.md); the scripts and per-line evidence are in
`sourcing/`.

# Contribute
- Feel free to fork it, add more quotes and do a pull merge request
- Please ensure that the quotes are real
- Please ensure that authors are in the first column, quotes in the second, sources (a JSON
  list, `[]` if unknown) in the third, separated by tabs
- Sources must be first-hand: the work in which the author wrote or said the line, not a
  website or book that merely quotes it
- Please update the statistics after you've added more quotes, do:
 - `wc -l author-quote.txt` to get no. of quotes
 - `cut -f1 author-quote.txt | sort | uniq | wc -l` to get no. of authors
 - `cut -f1,2 author-quote.txt | wc -w` to get no. of words
 - `cut -f3 author-quote.txt | grep -vc '^\[\]$'` to get no. of quotes with a first-hand source
