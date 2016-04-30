
import random

import yaml

class Grammar:

    """ A simpler version of Tracery's ideas. """

    def __init__( self, rules = None ):

        self.rules = rules or { }

        # To be pop()'d off by the caller.
        self.saved = [ ]

    def parse( self, string ):

        if "[" in string or "]" in string:

            fragments = [ ]
            buffer = ''

            brackets = False

            for char in string:
                if char == '[':
                    fragments += [ buffer ]
                    buffer = ''

                    if brackets:
                        raise Exception( "Grammar.parse: can't nest brackets" )

                    brackets = True

                elif char == ']':
                    if not brackets:
                        raise Exception( "Grammar.parse: unmatched bracket" )

                    brackets = False

                    # Mechanism for saving what result we got: put a ! somewhere in the [ ]-surrounded text.
                    if buffer.replace( "!", "" ) in self.rules:
                        fragments += [ self.parse( random.choice( self.rules[buffer.replace( "!", "" )] ) ) ]

                        if "!" in buffer:
                            self.saved += [ fragments[-1] ]

                        buffer = ''

                    else:
                        raise Exception( "Grammar.parse: no such rule '" + buffer + "'." )

                else:
                    buffer += char

            if buffer != '':
                fragments += [ buffer ]

            return "".join( fragments )

        else:
            return string

    def rule( self, rule, new = None ):

        if new:
            self.rules[rule] = new

        else:
            if rule in self.rules:
                return self.rules[rule]

            else:
                return None

wallMaker = Grammar({
    'wallMat': [ 'stone', 'rock', 'wood', 'paper', 'earth', 'crystal', 'leafy vagueness', 'sand', 'skin', 'bark', 'foliage', 'needles', 'delicate tiles', 'agate', 'quartz', 'glass', 'iron', 'copper' ],

    'wallCond': [ 'dark', 'heavy', 'slick', 'moss-clung', 'twisted', 'fluted', 'greenish', 'dark', 'hot', 'lumpy', 'unsteady', 'slippery', 'geometrically flanged', 'sigil-eaten', 'consuming', 'blue', 'reddish', 'translucent', 'ultramarine', 'sky-blue', 'delicate pink', 'fuligin' ],

    'walls': [ 'walls of [wallMat] close in; the way is [width].',
               '[wallCond] walls of [wallMat] close in.',
               'the walls are [wallCond] [wallMat]... the tunnels, [width].',
               'all around, [wallCond] [wallMat].',
               'all around, [wallMat].',
               'there\'s [wallMat] everywhere here.',
               'there\'s [wallMat] everywhere here. it\'s [wallCond].',
               '[wallCond] [wallMat] all around.',
               'the walls are made of [wallMat] here.',
               'this place is built entirely of [wallMat].',
               'it\'s very [wallCond] here.',

               '[width], [wallCond].',
               '[wallMat].',
               '[wallCond].'],

    'width': [ 'suffocatingly close', 'echoing', 'massive', 'wide', 'barely large enough to pass crawling', 'thin and straight', 'tall and narrow', 'tiny', 'spacious', 'vast' ],

    'door': [ 'door', 'hatch', 'gate', 'opening', 'incision', 'grating', 'well', 'oubliette', 'tunnel', 'arch' ],
    'doorMat': [ 'rock', 'oaken', 'papery', 'crystal', 'glass', 'iron', 'silver' ],

    'hidden': [ 'half-hidden', 'in plain view', 'almost impossible to spot', 'staring you in the face', 'which can only be found by touch' ]
})

if __name__ == '__main__':

    linkNames = [ "[N]orth;north;n", "[S]outh;south;s", "[E]ast;east;e", "[W]est;west;w", "[U]p;up;u" ]

    project = { "projectName": "maze", "rooms": { } }

    roomCount = 25

    for i in range(0, roomCount):

        desc = wallMaker.parse("[walls]\n\na [doorMat] [!door], [hidden].")
        door = wallMaker.saved.pop( )
        ID = "room-" + i.__str__()

        project["rooms"][ ID ] = { "NAME": "Maze" }
        project["rooms"][ ID ][ "LINKS" ] = { }
        project["rooms"][ ID ][ "_/de" ] = desc
        project["rooms"][ ID ][ "POSTSCRIPT" ] = { "BUILD": [ "@set here=D", "@tel here=#63" ] }

        # Each room shall have 2-3 links to other random rooms. Don't try to be consistent.
        ln = linkNames.copy( )
        random.shuffle(ln)

        for i in range( 0, random.choice([ 2, 3, 3, 3, 3, 4, 4, 4 ]) ):
            project["rooms"][ ID ][ "LINKS" ][ "room-" + random.choice( range(0, roomCount) ).__str__() ] = {
                "NAME": ln.pop( ),
                "succ": "You force your way through the " + door + ".",
                "osucc": "forces their way through the " + door + ".",
                "odrop": "emerges through an obscure way from some other part of the maze." }

    with open("maze.gen.yaml", "w") as fh:

        fh.write( yaml.dump( project ) )

    print( "write: maze.gen.yaml (probably.)" )
