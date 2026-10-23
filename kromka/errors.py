# -*- coding: utf-8 -*-
"""Vlastní výjimky."""


class NeresolvovanyClanek(Exception):
    """Z titulku se nepodařilo odvodit funkční adresu článku.

    Stává se u článků, kterým redakce po publikaci přepsala titulek — TYPO3
    generuje slug jen jednou při založení a pak ho nemění. Z feedu se taková
    adresa dopočítat nedá. Článek se zahodí, protože bez funkčního odkazu na
    originál bychom porušili vlastní pravidlo o atribuci.
    """
