Point Tracker
=============

The point tracker is most useful to compute and show growth and displacement 
fields on biological tissues. From a series of images of a biological sample 
over time, the user can select material points over the various images, create 
cells, and compute the growth rates for each cells over time.

Installation
------------

### From source

You can get the source either by cloning the repository or getting an archive 
that you uncompress. The application can then be used in-place, or you can 
install it with:

    $ python setup.py install

### Using pip

From pip, you can simply use:

    $ pip install point-tracker


Launching
---------

### When installed on the system

The setup script will create and install a ``point_tracker`` program on your 
system, that you simply need to launch:

    $ point_tracker

### From the source folder

From the source folder, you can use one of the tracking script:

    $ python tracking.py

Under Linux, you can also use the shell script:

    $ ./tracking.sh

Acknowledgements
----------------

If you are using this software for scientific purposes, please cite the 
following paper:

> Kuchen, E. E.; Fox, S.; Barbier de Reuille, P.; Kennaway, R.; Bensmihen, S.; 
> Avondo, J.; Calder, G. M.; Southam, P.; Robinson, S.; Bangham, A. & Coen, E. 
> **Generation of leaf shape through early patterns of growth and tissue 
> polarity**. *Science*. 2012, 335, 1092-1096

Bibtex reference:

    @Article{Kuchen12,
      Title                    = {Generation of leaf shape through early patterns of growth and tissue polarity.},
      Author                   = {Kuchen, Erika E and Fox, Samantha and {Barbier de Reuille}, Pierre and Kennaway, Richard and Bensmihen, Sandra and Avondo, Jerome and Calder, Grant M and Southam, Paul and Robinson, Sarah and Bangham, Andrew and Coen, Enrico},
      Journal                  = {Science},
      Year                     = {2012},
      Month                    = Mar,
      Number                   = {6072},
      Pages                    = {1092--1096},
      Volume                   = {335},
      Pii                      = {335/6072/1092},
      Pmid                     = {22383846},
    }

