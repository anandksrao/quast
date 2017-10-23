[![Release](https://img.shields.io/badge/Release-v2.3-blue.svg?style=flat)](https://github.com/lh3/minimap2/releases)
[![BioConda](https://img.shields.io/conda/vn/bioconda/minimap2.svg?style=flat)](https://anaconda.org/bioconda/minimap2)
[![PyPI](https://img.shields.io/pypi/v/mappy.svg?style=flat)](https://pypi.python.org/pypi/mappy)
[![Python Version](https://img.shields.io/pypi/pyversions/mappy.svg?style=flat)](https://pypi.python.org/pypi/mappy)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat)](LICENSE.txt)
[![Build Status](https://travis-ci.org/lh3/minimap2.svg?branch=master)](https://travis-ci.org/lh3/minimap2)
[![Downloads](https://img.shields.io/github/downloads/lh3/minimap2/total.svg?style=flat)](https://github.com/lh3/minimap2/releases)
## <a name="started"></a>Getting Started
```sh
git clone https://github.com/lh3/minimap2
cd minimap2 && make
# long reads against a reference genome
./minimap2 -a test/MT-human.fa test/MT-orang.fa > test.sam
# create an index first and then map
./minimap2 -d MT-human.mmi test/MT-human.fa
./minimap2 -a MT-human.mmi test/MT-orang.fa > test.sam
# long-read overlap (no test data)
./minimap2 -x ava-pb your-reads.fa your-reads.fa > overlaps.paf
# spliced alignment (no test data)
./minimap2 -ax splice ref.fa rna-seq-reads.fa > spliced.sam
# man page for detailed command line options
man ./minimap2.1
```
## Table of Contents

- [Getting Started](#started)
- [Users' Guide](#uguide)
  - [Installation](#install)
  - [General usage](#general)
  - [Use cases](#cases)
    - [Map long noisy genomic reads](#map-long-genomic)
    - [Map long mRNA/cDNA reads](#map-long-splice)
    - [Find overlaps between long reads](#long-overlap)
    - [Map short accurate genomic reads](#short-genomic)
    - [Full genome/assembly alignment](#full-genome)
  - [Advanced features](#advanced)
    - [Working CIGARs with >65535 operations](#long-cigar)
    - [The cs optional tag](#cs)
    - [Evaluation scripts](#eval)
  - [Algorithm overview](#algo)
  - [Getting help](#help)
  - [Citing minimap2](#cite)
- [Developers' Guide](#dguide)
- [Limitations](#limit)

## <a name="uguide"></a>Users' Guide

Minimap2 is a versatile sequence alignment program that aligns DNA or mRNA
sequences against a large reference database. Typical use cases include: (1)
mapping PacBio or Oxford Nanopore genomic reads to the human genome; (2)
finding overlaps between long reads with error rate up to ~15%; (3)
splice-aware alignment of PacBio Iso-Seq or Nanopore cDNA or Direct RNA reads
against a reference genome; (4) aligning Illumina single- or paired-end reads;
(5) assembly-to-assembly alignment; (6) full-genome alignment between two
closely related species with divergence below ~15%.

For ~10kb noisy reads sequences, minimap2 is tens of times faster than
mainstream long-read mappers such as BLASR, BWA-MEM, NGMLR and GMAP. It is more
accurate on simulated long reads and produces biologically meaningful alignment
ready for downstream analyses. For >100bp Illumina short reads, minimap2 is
three times as fast as BWA-MEM and Bowtie2, and as accurate on simulated data.
Detailed evaluations are available from the [minimap2 preprint][preprint].

### <a name="install"></a>Installation

Minimap2 only works on x86-64 CPUs. You can acquire precompiled binaries from
the [release page][release] with:
```sh
wget --no-check-certificate -O- https://github.com/lh3/minimap2/releases/download/v2.2/minimap2-2.2_x64-linux.tar.bz2 \
  | tar -jxvf -
./minimap2-2.2_x64-linux/minimap2
```
If you want to compile from the source, you need to have a C compiler, GNU make
and zlib development files installed. Then type `make` in the source code
directory to compile. If you see compilation errors, try `make sse2only=1`
to disable SSE4 code, which will make minimap2 slightly slower.

### <a name="general"></a>General usage

Without any options, minimap2 takes a reference database and a query sequence
file as input and produce approximate mapping, without base-level alignment
(i.e. no CIGAR), in the [PAF format][paf]:
```sh
minimap2 ref.fa query.fq > approx-mapping.paf
```
You can ask minimap2 to generate CIGAR at the `cg` tag of PAF with:
```sh
minimap2 -c ref.fa query.fq > alignment.paf
```
or to output alignments in the [SAM format][sam]:
```sh
minimap2 -a ref.fa query.fq > alignment.sam
```
Minimap2 seamlessly works with gzip'd FASTA and FASTQ formats as input. You
don't need to convert between FASTA and FASTQ or decompress gzip'd files first.

For the human reference genome, minimap2 takes a few minutes to generate a
minimizer index for the reference before mapping. To reduce indexing time, you
can optionally save the index with option **-d** and replace the reference
sequence file with the index file on the minimap2 command line:
```sh
minimap2 -d ref.mmi ref.fa                     # indexing
minimap2 -a ref.mmi reads.fq > alignment.sam   # alignment
```
***Importantly***, it should be noted that once you build the index, indexing
parameters such as **-k**, **-w**, **-H** and **-I** can't be changed during
mapping. If you are running minimap2 for different data types, you will
probably need to keep multiple indexes generated with different parameters.
This makes minimap2 different from BWA which always uses the same index
regardless of query data types.

### <a name="cases"></a>Use cases

Minimap2 uses the same base algorithm for all applications. However, due to the
different data types it supports (e.g. short vs long reads; DNA vs mRNA reads),
minimap2 needs to be tuned for optimal performance and accuracy. It is usually
recommended to choose a preset with option **-x**, which sets multiple
parameters at the same time. The default setting is the same as `map-ont`.

#### <a name="map-long-genomic"></a>Map long noisy genomic reads

```sh
minimap2 -ax map-pb  ref.fa pacbio-reads.fq > aln.sam   # for PacBio subreads
minimap2 -ax map-ont ref.fa ont-reads.fq > aln.sam      # for Oxford Nanopore reads
```
The difference between `map-pb` and `map-ont` is that `map-pb` uses
homopolymer-compressed (HPC) minimizers as seeds, while `map-ont` uses ordinary
minimizers as seeds. Emperical evaluation suggests HPC minimizers improve
performance and sensitivity when aligning PacBio reads, but hurt when aligning
Nanopore reads.

#### <a name="map-long-splice"></a>Map long mRNA/cDNA reads

```sh
minimap2 -ax splice ref.fa spliced.fq > aln.sam      # strand unknown
minimap2 -ax splice -uf ref.fa spliced.fq > aln.sam  # assuming transcript strand
```
This command line has been tested on PacBio Iso-Seq reads and Nanopore 2D cDNA
reads, and been shown to work with Nanopore 1D Direct RNA reads by others. Like
typical RNA-seq mappers, minimap2 represents an intron with the `N` CIGAR
operator. For spliced reads, minimap2 will try to infer the strand relative to
transcript and may write the strand to the `ts` SAM/PAF tag.

#### <a name="long-overlap"></a>Find overlaps between long reads

```sh
minimap2 -x ava-pb  reads.fq reads.fq > ovlp.paf    # PacBio read overlap
minimap2 -x ava-ont reads.fq reads.fq > ovlp.paf    # Oxford Nanopore read overlap
```
Similarly, `ava-pb` uses HPC minimizers while `ava-ont` uses ordinary
minimizers. It is usually not recommended to perform base-level alignment in
the overlapping mode because it is slow and may produce false positive
overlaps. However, if performance is not a concern, you may try to add `-a` or
`-c` anyway.

#### <a name="short-genomic"></a>Map short accurate genomic reads

```sh
minimap2 -ax sr ref.fa reads-se.fq > aln.sam           # single-end alignment
minimap2 -ax sr ref.fa read1.fq read2.fq > aln.sam     # paired-end alignment
minimap2 -ax sr ref.fa reads-interleaved.fq > aln.sam  # paired-end alignment
```
When two read files are specified, minimap2 reads from each file in turn and
merge them into an interleaved stream internally. Two reads are considered to
be paired if they are adjacent in the input stream and have the same name (with
the `/[0-9]` suffix trimmed if present). Single- and paired-end reads can be
mixed.

Minimap2 does not work well with short spliced reads. There are many capable
RNA-seq mappers for short reads.

#### <a name="full-genome"></a>Full genome/assembly alignment

```sh
minimap2 -ax asm5 ref.fa asm.fa > aln.sam       # assembly to assembly/ref alignment
```
For cross-species full-genome alignment, the scoring system needs to be tuned
according to the sequence divergence.

### <a name="advanced"></a>Advanced features

#### <a name="long-cigar"></a>Working CIGARs with >65535 operations

Due to a design flaw, BAM does not work with CIGAR strings with >65535
operations (SAM and CRAM work). However, for ultra-long nanopore reads minimap2
may align ~1% of read bases with long CIGARs beyond the capability of BAM. If
you convert such SAM/CRAM to BAM, Picard and recent samtools will throw an
error and abort. Older samtools and other tools may create corrupted BAM.

To avoid this issue, you can add option `-L` at the minimap2 command line.
This option moves a long CIGAR to the `CG` tag and leaves a fully clipped CIGAR
at the SAM CIGAR column. Current tools that don't read CIGAR (e.g. merging and
sorting) still work with such BAM records; tools that read CIGAR will
effectively ignore these records. I have pull requests to the SAM spec, htslib,
htsjdk, bedtools2, Rsamtools and igv.js. If they are accepted, future versions
of these tools will seamlessly recognize long-cigar records generated by option
`-L`.

**TD;DR**: if you work with ultra-long reads and use tools that only process
BAM files, please add option `-L`.

#### <a name="cs"></a>The cs optional tag

The `cs` SAM/PAF tag encodes bases at mismatches and INDELs. It matches regular
expression `/(:[0-9]+|\*[a-z][a-z]|[=\+\-][A-Za-z]+)+/`. Like CIGAR, `cs`
consists of series of operations.  Each leading character specifies the
operation; the following sequence is the one involved in the operation.

The `cs` tag is enabled by command line option `--cs`. The following alignment,
for example:
```txt
CGATCGATAAATAGAGTAG---GAATAGCA
||||||   ||||||||||   |||| |||
CGATCG---AATAGAGTAGGTCGAATtGCA
```
is represented as `:6-ata:10+gtc:4*at:3`, where `:[0-9]+` represents an
identical block, `-ata` represents a deltion, `+gtc` an insertion and `*at`
indicates reference base `a` is substituted with a query base `t`. It is
similar to the `MD` SAM tag but is standalone and easier to parse.

If `--cs=long` is used, the `cs` string also contains identical sequences in
the alignment. The above example will become
`=CGATCG-ata=AATAGAGTAG+gtc=GAAT*at=GCA`. The long form of `cs` encodes both
reference and query sequences in one string.

#### <a name="eval"></a>Evaluation scripts

Minimap2 comes with several (java)scripts for evaluating the accuracy of
minimap2. These scripts require the [k8][k8] javascript shell to run.
Recent minimap2 binary release tar-balls contain a copy of k8 executable, a
single file. Here are a few examples on how to use these scripts:

```sh
# Generate reads from PBSIM alignment (truth encoded in read names)
k8 misc/sim-pbsim.js ref.fa.fai pbsim-aln.maf > pbsim-reads.fq
# Generate reads from mason2 alignment (not tested for simulated SVs)
k8 misc/sim-mason2.js mason2-aln.sam > mason2-reads.fq
# Evaluate mapping accuracy with ROC-like curve
k8 misc/sim-eval.js my-aln.sam.gz > result.txt
k8 misc/sim-eval.js my-aln.paf.gz > result.txt
# Collect alignment statistics
k8 misc/mapstat.js my-aln.sam > result.txt
# Compare spliced junctions to existing gene annotations
k8 misc/intron-eval.js anno.gtf my-spliced-aln.sam > result.txt
```

### <a name="algo"></a>Algorithm overview

In the following, minimap2 command line options have a dash ahead and are
highlighted in bold. The description may help to tune minimap2 parameters.

1. Read **-I** [=*4G*] reference bases, extract (**-k**,**-w**)-minimizers and
   index them in a hash table.

2. Read **-K** [=*200M*] query bases. For each query sequence, do step 3
   through 7:

3. For each (**-k**,**-w**)-minimizer on the query, check against the reference
   index. If a reference minimizer is not among the top **-f** [=*2e-4*] most
   frequent, collect its the occurrences in the reference, which are called
   *seeds*.

4. Sort seeds by position in the reference. Chain them with dynamic
   programming. Each chain represents a potential mapping. For read
   overlapping, report all chains and then go to step 8. For reference mapping,
   do step 5 through 7:

5. Let *P* be the set of primary mappings, which is an empty set initially. For
   each chain from the best to the worst according to their chaining scores: if
   on the query, the chain overlaps with a chain in *P* by **--mask-level**
   [=*0.5*] or higher fraction of the shorter chain, mark the chain as
   *secondary* to the chain in *P*; otherwise, add the chain to *P*.

6. Retain all primary mappings. Also retain up to **-N** [=*5*] top secondary
   mappings if their chaining scores are higher than **-p** [=*0.8*] of their
   corresponding primary mappings.

7. If alignment is requested, filter out an internal seed if it potentially
   leads to both a long insertion and a long deletion. Extend from the
   left-most seed. Perform global alignments between internal seeds.  Split the
   chain if the accumulative score along the global alignment drops by **-z**
   [=*400*], disregarding long gaps. Extend from the right-most seed.  Output
   chains and their alignments.

8. If there are more query sequences in the input, go to step 2 until no more
   queries are left.

9. If there are more reference sequences, reopen the query file from the start
   and go to step 1; otherwise stop.

### <a name="help"></a>Getting help

Manpage [minimap2.1](minimap2.1) provides detailed description of minimap2
command line options and optional tags. If you encounter bugs or have further
questions or requests, you can raise an issue at the [issue page][issue].
There is not a specific mailing list for the time being.

### <a name="cite"></a>Citing minimap2

If you use minimap2 in your work, please consider to cite:

> Li, H. (2017). Minimap2: fast pairwise alignment for long nucleotide sequences. [arXiv:1708.01492][preprint]

## <a name="dguide"></a>Developers' Guide

Minimap2 is not only a command line tool, but also a programming library.
It provides C APIs to build/load index and to align sequences against the
index. File [example.c](example.c) demonstrates typical uses of C APIs. Header
file [minimap.h](minimap.h) gives more detailed API documentation. Minimap2
aims to keep APIs in this header stable. File [mmpriv.h](mmpriv.h) contains
additional private APIs which may be subjected to changes frequently.

This repository also provides Python bindings to a subset of C APIs. File
[python/README.rst](python/README.rst) gives the full documentation;
[python/minimap2.py](python/minimap2.py) shows an example. This Python
extension, mappy, is also [available from PyPI][mappypypi] via `pip install
mappy` or [from BioConda][mappyconda] via `conda install -c bioconda mappy`.

## <a name="limit"></a>Limitations

* Minimap2 may produce suboptimal alignments through long low-complexity
  regions where seed positions may be suboptimal. This should not be a big
  concern because even the optimal alignment may be wrong in such regions.

* Minimap2 requires SSE2 instructions to compile. It is possible to add
  non-SSE2 support, but it would make minimap2 slower by several times.

In general, minimap2 is a young project with most code written since June, 2017.
It may have bugs and room for improvements. Bug reports and suggestions are
warmly welcomed.



[paf]: https://github.com/lh3/miniasm/blob/master/PAF.md
[sam]: https://samtools.github.io/hts-specs/SAMv1.pdf
[minimap]: https://github.com/lh3/minimap
[smartdenovo]: https://github.com/ruanjue/smartdenovo
[longislnd]: https://www.ncbi.nlm.nih.gov/pubmed/27667791
[gaba]: https://github.com/ocxtal/libgaba
[ksw2]: https://github.com/lh3/ksw2
[preprint]: https://arxiv.org/abs/1708.01492
[release]: https://github.com/lh3/minimap2/releases
[mappypypi]: https://pypi.python.org/pypi/mappy
[mappyconda]: https://anaconda.org/bioconda/mappy
[issue]: https://github.com/lh3/minimap2/issues
[k8]: https://github.com/attractivechaos/k8