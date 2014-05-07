UIFILES=$(wildcard *.ui)
RCFILES=icons.qrc
GENERATED=$(patsubst %.ui,ui_%.py,$(UIFILES)) $(patsubst %.qrc,%_rc.py,$(RCFILES)) ui_tracking_window_macos.py
UI_IMPL=$(patsubst %.ui,%.py,$(patsubst tracking_window.ui,,$(UIFILES)))

PYFILES=tracking.py $(wildcard tracking_*.py) trackingview.py algo.py geometry.py utils.py image_cache.py \
	normcross.py parameters.py project.py timemodel.py growth_algo.py growth_computation_methods.py \
	$(UI_IMPL) qtransferfunctionviewer.py transferfunction.py plotting_methods.py sys_utils.py \
	debug.py scale_bar.py $(wildcard tissue_plot/*.py)

default: icons_rc.py

all: $(GENERATED)

PYUIC4 ?= pyuic4
PYRCC4 ?= pyrcc4

PYRCC_FLAGS = -py3 # Careful with python version!
PYUIC_FLAGS = --from-imports

gui:
	designer $(UIFILES)&

edit:
	gvim $(PYFILES)

ipython: $(GENERATED) tracking.py
	ipython tracking.py

tracking.py:
	ln -s tracking.pyw tracking.py

ui_%.py: %.ui
	$(PYUIC4) $(PYUIC_FLAGS) $< -o $@

%_rc.py: %.qrc
	$(PYRCC4) $(PYRCC_FLAGS) -o $@ $<

shell: $(GENERATED)
	ipython -q4thread -c "from tracking import *; mw = ipython()"
#	ipython tracking.py

terminal: $(GENERATED)
	gnome-terminal -e 'ipython -q4thread -x "from tracking import *; mw = ipython()"'
#	gnome-terminal -e 'ipython tracking.py'

run: $(GENERATED) tracking.py
	python tracking.py

clean:
	rm -f $(GENERATED) *.pyc

docgui: ${PYFILES} ${GENERATED} path.py
	epydocgui ${PYFILES} path.py
	#touch doc

doc: ${PYFILES} ${GENERATED} path.py
	epydoc -v --html -n "Point tracking" ${PYFILES} path.py
	touch doc

#         epydoc -v -n "Point tracking" --docformat=restructuredtext --graph=all --dotpath=/usr/bin/dot $^

light_doc: tracking.py tracking_data.py
	epydoc -v -n "Point tracking" --docformat=restructuredtext $^
	touch light_doc

