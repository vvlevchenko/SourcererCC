# SourcererCC

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/86471e8cabf74c6486622d9027c1c0d3)](https://app.codacy.com/app/rprtr258/SourcererCC?utm_source=github.com&utm_medium=referral&utm_content=rprtr258/SourcererCC&utm_campaign=Badge_Grade_Settings)
[![Build Status](https://travis-ci.com/rprtr258/SourcererCC.svg?branch=master)](https://travis-ci.com/rprtr258/SourcererCC)

## How to run

Write urls of repositories you want to analyze in **urls.txt**. Then execute:

```bash
./run.py
```

## Old README

## Tutorial

SourcererCC is [Sourcerer](http://sourcerer.ics.uci.edu/ "Sourcerer Project @ UCI")'s token-based code clone detector for very large code bases and Internet-scale project repositories. SourcererCC works at many levels of granularity such as detecting clones between files, methods, statements or blocks, in any language. This tutorial is for file-level clone detection on Java.

### Additional Resources

*   For more information about SourcererCC please see the [ICSE'16](http://arxiv.org/abs/1512.06448) paper.
*   SourcererCC supports DéjàVu, a large scale study of cloning on GitHub. It has a [homepage](http://mondego.ics.uci.edu/projects/dejavu/), and was published at [OOPSLA'17](https://dl.acm.org/citation.cfm?id=3133908)
*   DéjàVu is a supporting web-tool to allow quick and simple clone analysis, can be found [here](http://dejavu.ics.uci.edu/).

### Before going through

We have created an artifact in the form of a virtual machine (VM) that contains the pre-programmed set of instructions that take the user from raw source code to a database with a clone mapping, including all the intermediate steps and explanation of intermediate data types. It can be downloaded from the 'Source Materials' section of the [paper ACM website](https://dl.acm.org/citation.cfm?id=3133908) or from the [DéjàVu homepage](http://mondego.ics.uci.edu/projects/dejavu/) (only the latter is kept updated).
This VM is the easiest way to get started with SourcererCC to perform your own clone analysis. It has most of the information here. **Please try this VM before contacting us.**

Let's get started.

## Table of Contents
1. Tokenize source code
2. Run SourcererCC
3. I want to know more!

### Tokenize source code

SourcererCC is a token-based clone detector. This means that source code must go through an initial step of processing. Luckily, we have a tool do to so, which we will explain in this section.

The program needed to tokenize souce code can be found [here](https://github.com/Mondego/SourcererCC/tree/master/tokenizers/file-level). Start by looking at [config.ini](https://github.com/Mondego/SourcererCC/blob/master/tokenizers/file-level/config.ini) which sets the configuration for the tokenizer. You need to edit a few parameters (the parameters not covered here can be dismissed for now):

Performance parameters:
```bash
N_PROCESSES = 1
; How many projects does each process process at a time?
PROJECTS_BATCH = 2
``` 

Where `N_PROCESSES` are active at any given time, and each one processes a batch of `PROJECTS_BATCH` projects.

To set the input you can do:
```bash
FILE_projects_list = this/is/a/path/paths.txt
```
where `paths.txt` is a list of project paths, the projects we want to find clones on. A sample of a `paths.txt` file would look like this:

```
path/for/projects/aesthetic-master.zip
path/for/projects/aesthetic-master.zipOffsetAnimator-master.zip
path/for/projects/aesthetic-master.zipResourceInspector-master.zip
path/for/projects/aesthetic-master.zipzachtaylor-JPokemon.zip
```

Language configurations. Since comments are removed you need to set the language primitives for `comment_inline` and `comment_open_tag`/`comment_close_tag` comments. Finally, describe the `File_extensions` being analyzed (supports a list of extensions):
```
[Language]
comment_inline = //
comment_open_tag = /*
comment_close_tag = */
File_extensions = .py
```
And then run with:
```bash
python tokenizer.py zip
```
where `zip` is the extension of the individual projects in `FILE_projects_list = this/is/a/path/paths.txt`. 

The resulting output is composed of three folders, in the same location:
*   `bookkeeping_projs/*.projs` - contains a list of processed projects. Has the following format:

`project_id, project_path, project_url`

*   `files_stats/` - contains lists of files(blocks) together with statistics. Has the following format:

`project_id, file_id, file_path, file_url, file_hash, file_size, lines, lines_of_code(LOC), source_lines_of_code(SLOC)`

in blocks-mode contains files in format:

`'f', project_id, file_id, file_path, file_url, file_hash, file_size, lines, lines_of_code(LOC), source_lines_of_code(SLOC)`

and blocks in format:

`'b', project_id, block_id, block_hash, block_lines, block_LOC, block_SLOC, start_line, end_line`

*   `files_tokens/` - contains lists of files together with tokens statistics and the tokenized forms. Has the following format:
`project_id, file_id, total_tokens, unique_tokens, tokens_hash@#@token1@@::@@frequency,token2@@::@@frequency,...`

in blocks-mode  in `blocks_tokens/` contains:

`project_id, block_id, total_tokens, unique_tokens[, experimental_values], tokens_hash, tokens`

`block_id` is `"relative_id"` + `"file_id"`

The elements `file id` and `project id` always point to the same source code file or project, respectively (they work as a primary key). So a line in `files_stats/*` that start with `1,1` represents the same file as the line in `files_tokens/*` that starts with `1,1`, and these came from the project in `bookkeeping_projs/*` whose line starts with `1`.
The number of lines in `bookkeeping_projs/*` corresponds to the total number of projects analyzed, the number of lines in `files_stats/*` is the same as `files_tokens/*` and is the same as the total number of files obtained from the projects.

### Run SourcererCC

For this step we will run SourcererCC, which can be found [here](https://github.com/Mondego/SourcererCC/tree/master/clone-detector).

Start with `files_tokens/` from the previous step:

```bash
cat files_tokens/* > blocks.file
cp blocks.file SourcererCC/clone-detector/input/dataset/
```

Inside [clone-detector/](https://github.com/Mondego/SourcererCC/tree/master/clone-detector) it is worth looking at [sourcerer-cc.properties](https://github.com/Mondego/SourcererCC/blob/master/clone-detector/sourcerer-cc.properties), in particular at:

```bash
# Ignore all files outside these bounds
MIN_TOKENS=65
MAX_TOKENS=500000
```
where you can set an upper and lower bound for file clone detection. You can dismiss the other parameters for now.

To change the percentage of clone similarity, look at [runnodes.sh](https://github.com/Mondego/SourcererCC/blob/master/clone-detector/runnodes.sh#L9), line 9:

```bash
threshold="${3:-8}"
```
where `8` means clones will be flagged at 80% similarity (current setup), `7` at 70%, and so on.
The JVM parameters can be configured in the [same file](https://github.com/Mondego/SourcererCC/blob/master/clone-detector/runnodes.sh#L20), at line 20.

Finally, run:

```bash
python controller.py
```
This tool splits the task by multiple nodes, which must be aggregated in the end:

```bash
cat clone-detector/NODE_*/output8.0/query_* > results.pairs
```

The resulting information is a list of file id pairs which are clones. These ids correspond to the ids
generated in the tokenization phase. An example output is:

```
1,2
2,3
```

In this case we have the clone pairs `(1,2)` and `(2,3)`. To know which file corresponds to `1`, we can look at the folder `files_stats/*` and look for the line with the unique id `1`.

### I want to know more

That is great :+1: In the VM we refer to above you can find instructions and programs to import everything into an easily queryable database and perform statistic analysis on this information.
Our [OOPSLA'17](https://dl.acm.org/citation.cfm?id=3133908) paper is a great way to understand out typical pipeline and which kind of results you can obtain.
Finally, if you have any question or need more technical help (tweaking performance parameters for you hardware, for example), feel free to [contact us](http://mondego.ics.uci.edu/).
