#!/usr/bin/gmake

SEARCHPATH=$(subst :, ,$(PATH))
findcmd=$(firstword $(wildcard $(foreach cmd,$(cmds),$(addsuffix /$(cmd),$(SEARCHPATH)))))

cmds=inkscape inkscape.exe
INKSCAPE:=$(findcmd)
ifeq ($(strip $(INKSCAPE)),)
INKSCAPE :=
FIGURES :=
else
FIGURESBASE = $(basename $(wildcard figures/*.svg))
FIGURES = $(addsuffix .pdf,$(FIGURESBASE) )
endif

PAPERS = uc-contracts
TARGET_SUFFIXES = .pdf
TARGETS = $(foreach suffix,$(TARGET_SUFFIXES),$(addsuffix $(suffix),$(PAPERS)))

SRC_SUFFIXES = .tex .svg # Sources - Never erase these
PRECIOUS_SUFFIXES = .aux .bbl .nls .nlo .flt .synctex.gz
PRECIOUS_DEPENDS = $(addprefix %,$(PRECIOUS_SUFFIXES) $(SRC_SUFFIXES))
.PRECIOUS: $(PRECIOUS_DEPENDS) $(FIGURES) flatex
.PHONY: all

all: $(TARGETS)

%.pdf: %.tex %.bbl $(FIGURES)
	$(RM) $@
	touch $*.aux
	pdflatex $(PDFLATEXFLAGS) $<
	((grep -q "Rerun to get cross-references" $*.log) && \
		pdflatex $<) || echo "Running PDFLatex once was enough"

%.bbl: %.aux
	(grep -q bibdata $? && bibtex $*) || (touch $@)

%.aux %.nlo: %.tex $(FIGURES)
	touch $@
	pdflatex $(PDFLATEXFLAGS) $<

%.pdf : %.svg
	$(INKSCAPE) -z -f $?  --export-ignore-filters -A $@
