# Witsuwit'en Literacy

Self-paced lessons in reading and writing Witsuwit'en, taught by
Sharon Hargus in 2019–2020 and posted here as a free resource.

The site is a sibling of [`wittexts`](https://github.com/sharonhargus/wittexts),
[`sahtexts`](https://github.com/sharonhargus/sahtexts),
[`kwatexts`](https://github.com/sharonhargus/kwatexts), and
[`degxinag`](https://github.com/sharonhargus/degxinag) — same overall
shape (HTML on GitHub Pages, media on Internet Archive), simpler
structure (no IGT alignment).

## Live URL

`https://<owner>.github.io/witliteracy/` — set after the repo is
pushed and Pages is enabled.

## Layout

```
witliteracy/
├── index.html          # landing
├── courses.html        # menu: Literacy 1 / Literacy 2
├── about.html          # author / hosting / reuse
├── literacy_1/index.html
├── literacy_2/index.html
├── units/lit{1,2}-NN.html      # 16 generated session pages
├── pdfs/literacy_{1,2}/*.pdf   # worksheets + answer keys
├── css/main.css        # forked from wittexts
├── imgs/               # header bg, favicon
├── manifest.yaml       # session metadata (titles, dates, IA paths)
└── tools/
    ├── build_units.py     # regenerates units/ + per-course index
    └── extract_titles.py  # one-shot: pulls title candidates from PDFs
```

## Editing the site

- **Change a session title or blurb** → edit `manifest.yaml`, then
  run `python tools/build_units.py`.
- **Add a session** → append an entry to the right `literacy_*` list
  in `manifest.yaml` (give it a new `id` like `lit2-09`), then rebuild.
- **Change the visual style** → edit `css/main.css` directly. No
  rebuild needed.
- **Edit landing / about / courses pages** → those three are
  hand-maintained HTML; edit them directly.

## Internet Archive

The lecture videos live on a single IA item whose id is set at the top
of `manifest.yaml` as `ia_item:`. The full video URL for a session is

```
https://archive.org/download/{ia_item}/{video_path}
```

Until the videos are uploaded the embedded `<video>` tags will 404,
but every other piece of the site renders. To upload, the IA CLI
works fine:

```bash
pip install internetarchive
ia configure   # prompts for credentials
ia upload witsuwiten-literacy \
    /path/to/wit_literacy/Witsuwit_en_literacy_1/*.mp4 \
    /path/to/wit_literacy/Witsuwit_en_literacy_2/*.mp4 \
    --metadata="title:Witsuwit'en Literacy" \
    --metadata="creator:Sharon Hargus" \
    --metadata="subject:Witsuwit'en;language;literacy" \
    --metadata="mediatype:movies"
```

The mp4 filenames in the source directories don't quite match the
`video_path` values in `manifest.yaml` (the manifest renames each
file to a flat `literacy_N/<date>(_<n>).mp4` form so the URLs stay
predictable). Renaming on disk before upload is the simplest path; the
alternative is to use `ia upload --remote-name`.

## Deploy

GitHub Pages is configured via `.github/workflows/static.yml` (forked
verbatim from `wittexts`). Pushing to `main` triggers an automatic
deploy of the entire repo as the static site.

## Author

[Sharon Hargus](http://faculty.washington.edu/sharon/),
University of Washington Department of Linguistics.
