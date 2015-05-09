
# Rado Ivanov - 8/20/2013
# Make-file for the CIS400/4001 Progress Report Specification

	# Filenames to be-used in compilation
MAIN=progress_report
TEX=progress_report.tex

	# Core compilation commands
CC=pdflatex
BB=bibtex

all:$(TEX)
	$(CC) $(TEX)
	$(CC) $(TEX)

	rm -rf *.log *.aux *.bbl *.blg

clean:
	rm -rf *.log *.aux *.bbl *.blg

