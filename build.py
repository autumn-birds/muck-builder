
import sys # .argv
import re
import copy # .deepcopy( )

import yaml

def mergeDict( source, dest ):

    """Set dest[k] = source[k] for all k in source, doing so recursively for subdictionaries. This
    allows existing entries in source to be preserved."""

    for key in source.keys( ):

        if type( source[key] ) != dict:

            dest[key] = source[key]

        else:

            if key in dest and type( dest[key] ) == dict:
                mergeDict( source[key], dest[key] )

            else:
                # It WILL override if it's just a string or None or something.
                dest[key] = source[key]

class MuckObject:

    """Generic 'muck object'. Won't actually create an object, but knows how to do the relatively
    universal property setting, etc."""

    def __init__ ( self, ID, project ):

        self.id = ID
        self._name = "Generic Object"

        if type( project ) != Project:
            raise Exception( "MuckObject.__init__: no (valid) project given!" )

        self._project = project

        self._props = {}

        # Store the user's custom commands to help with creating / destroying this particular
        # object, or things related to it:

        self._buildPostscript = [ ]
        self._destroyPostscript = [ ]

    def regname ( self, projectID = "no-project" ):

        """Return the name used to register this room in the MUCK software, without a $
        prepended."""

        return "autodig/" + self._project.name + "/" + self.id

    def setProp ( self, propName, val ):

        """Parse / record a particular property/property-value combination. If the property
        ends with a #, it will be saved on the room as a list."""

        # Otherwise, a yaml > with multiple paragraphs will give you only one new-line
        # between the paragraphs. So this is like a special syntax for 'extra newline.'
        val = val.replace ( "**", "\n" )

        if propName[-1] == '#':
            self._props[propName[0:-1]] = val.split ( "\n" )
        else:
            # We will also make MPI out of any newlines in ordinary string props.
            self._props[propName] = val.replace( "\n", "{nl}" )

    def addUserCommand ( self, cmd, context = "BUILD" ):

        """Record a custom command the user wants to use to do something fancy/special/different to
        this object. Will be returned by .postProcess( ) with interpolations as described by
        .interpolateString( )."""

        if context == "BUILD":
            self._buildPostscript += [ cmd ]
            return cmd

        if context == "DESTROY":
            self._destroyPostscript += [ cmd ]
            return cmd

        raise Exception( "Weird context for commands: '" + context + "'." )

    def setName ( self, name ):

        """Sets object's 'name'. The name is not actually @name'd by MuckObject's methods, but most
        derivations of MuckObject should probably use it when building the object. This is
        distinctly different from the name the object is REGISTERED under."""

        self._name = name

    def getName ( self ):

        """Return the object's 'name'."""

        return self._name

    def interpolateString( self, string ):

        """Return a (command) string with certain values replaced in: !R for object reference, !N
        for self.getName( ). Not an actual parsing system, so ! anywhere else is just !."""

        k = string

        k = k.replace( "!R", self.regname( ) )
        k = k.replace( "!N", self.getName( ) )

        return k

    def props ( self ):

        """Dictionary of our properties."""

        return self._props

    def realise ( self ):

        """Generate MUCK commands: (re)set all properties, etc., on the MuckObject (by
        registered name.)

        Normally, child types should use this implementation, and implement 'build' to
        create the object itself, and etc."""

        k = [ ]

        for prop in self._props.keys ():

            if type( self._props[prop] ) == list:
                k += [ "lsedit $" + self.regname ( ) + "=" + prop,
                       ".del 1 999" ]                                   # Make sure it's empty
                k += [ line + "  " for line in self._props[prop] ]
                k += [ ".end" ]

            else:
                k += [ "@set $" + self.regname ( ) + "=" + prop + ":" + self._props[prop] ]

        return k

    def postProcess( self, context = "BUILD" ):

        k = self._buildPostscript

        if context == "DESTROY":
            k = self._destroyPostscript

        k = [ self.interpolateString( line ) for line in k ]

        return k

    def remove ( self ):

        """Return MUCK commands to remove the object and its registration."""

        return [ "@recycle " + "$" + self.regname ( ),
                 "@set " + "me=/_reg/" + self.regname ( ) + ":" ]


class Room ( MuckObject ):

    def __init__ ( self, ID, project ):

        super ( Room, self ).__init__ ( ID, project )

        self._name = "Untitled Room"
        self._parent = ""

        self._props = {}

        self._exits = []                # Not keyed; multiple exits can point -> same room.

    def addExit ( self, exit ):

        """Add an exit to the room."""

        if type( exit ) == Link and exit.orig( ) == self.getID( ):
            self._exits += [exit]

        else:
            raise TypeError( "The exit is not an exit or does not link to this room." )

    def exits ( self ):

        """List of exits originating in this room."""

        return self._exits

    def getID( self ):

        return self.id

    def build ( self ):

        """Generate MUCK commands: create the room and write properties to it."""

        return [ "@dig " + self._name + "==" + self.regname ( ) ] \
                + self.realise ()

    def postProcess( self, context = "BUILD" ):

        """Teleport into the room, and then run the 'post-processing' commands as normal."""

        k = [ ]

        if len( ( context == "BUILD" and self._buildPostscript ) or self._destroyPostscript ) > 0:

            # I think on SpinDizzy this has to be 'tel ' + <roomDBRefOrID> -- but that doesn't work on
            # the test server I was using, so I don't know. Maybe it should be customisable?
            k += [ "@tel me=" + "$" + self.regname( ) ]
            k += super( Room, self ).postProcess( )

        return k


class Link ( MuckObject ):

    # Really an exit.
    #
    # (No, really an action.)

    def __init__ ( self, orig, dest, project ):

        self._orig = orig
        self._dest = dest

        super ( Link, self ).__init__ ( self.getID ( ), project )

        self._name = "[G]eneric [E]xit;exit;ge"

    def sanityCheck ( self ):

        """Make sure our origin and destination are actually rooms registered to the project -- if
        not, raise a more-helpful error message/Exception."""

        if not self._project.room( self._orig ):
            raise Exception("Link.__init__: no such room to link from: '" + self._orig + "'!")

        if not self._project.room( self._dest ):
            raise Exception("Link.__init__: no such room to link to: '" + self._dest + "'!")

    def getID ( self ):

        return "LINK-" + self._orig + "-TO-" + self._dest

    def orig( self ):

        """Get originating room-name."""

        return self._orig

    def dest( self ):

        """Get destination ('target') room-name."""

        return self._dest

    def build ( self ):

        self.sanityCheck( )

        return [ "@action " + self._name + "=$" + self._project.room( self._orig ).regname( ) + \
                     "=" + self.regname( ),
                 "@link " + "$" + self.regname( ) + "=$" + self._project.room( self._dest ).regname ( ) ] \
               + self.realise( )

    def realise ( self ):

        """See also MuckObject.realise( )."""

        self.sanityCheck( )

        if self._project.config["sge"]:
            self.sge( )

        k = [ ]

        # Let's get ready to fool super.realise() into thinking we don't have certain special properties
        # that need to be given as @commands instead. I'm aware this is probably not the best way to do
        # this.
        temp = self._props

        for cmd in [ "succ", "osucc", "drop", "odrop" ]:

            if cmd in self._props:
                k += [ "@" + cmd + " $" + self.regname( ) + "=" + self._props.pop( cmd ) ]

        k += super( Link, self ).realise( )

        # ...but we don't want to forget about said props in case we need to do this again...
        self._props = temp

        # Side note: you don't actually need to use the @commands. The properties _/osc, _/sc,
        # _/dr and _/odr work, according to help [@osucc and friends] on FuzzBall. By the time I
        # realised that I had already begun to make this, and suspect people might be less confused/
        # intimidated than by all the underscores and slashes and cryptically abbreviated names anyway.

        return k

    def sge ( self ):

        """If any of succ (_/sc), osucc (_/osc), or odrop (_/odr) are unset, provide a generic
        message."""

        self.sanityCheck( )

        for prop in [ ["succ", "_/sc"], ["osucc", "_/osc"], ["odrop", "_/odr"], ["drop", "_/dr"] ]:

            if prop[0] in self._props or prop[1] in self._props:
                pass

            else:
                if prop[0] == "succ":
                    self.setProp( "succ", self._project.room( self._dest ).interpolateString( \
                                            self._project.config["sge"]["succ"] or "You leave for !N." ) )

                if prop[0] == "osucc":
                    self.setProp( "osucc", self._project.room( self._dest ).interpolateString( \
                                            self._project.config["sge"]["osucc"] or "leaves for !N." ) )

                if prop[0] == "odrop":
                    self.setProp( "osucc", self._project.room( self._orig ).interpolateString( \
                                            self._project.config["sge"]["odrop"] or "arrives from !N." ) )

                if prop[0] == "drop":
                    if "drop" in self._project.config["sge"]:
                        self._props["drop"] = self._project.room( self._dest ).interpolateString( \
                                               self._project.config["sge"]["drop"] )

class Project:

    def __init__ ( self, name ):

        self.name = name

        self._rooms = { }
        self._exits = [ ]

        self._buildPostscript  = [ ]
        self._destroyPostscript = [ ]

        self.config = {
            "sge?": True,
            "sge": {
                "osucc": None,
                "succ": None,
                "odrop": None
            }
        }

    def configure( self, key, val ):

        mergeDict( { key: val }, self.config )

    def addUserCommand ( self, cmd, context = "BUILD" ):

        if context == "BUILD":
            self._buildPostscript += [ cmd ]
            return cmd

        if context == "DESTROY":
            self._destroyPostscript += [ cmd ]
            return cmd

        raise Exception( "Weird context for commands: '" + context + "'." )

    def applyProps ( self, props, room ):

        """Apply the block of properties given ('props') to the room named in parameter
        'room'. Parses all special properties such as 'NAME' and exits."""

        if not room in self._rooms.keys():
            self._rooms[room] = Room ( room, self )

        # Deal with adding 'user commands' to the room.
        for ( context, commands ) in props.pop( "POSTSCRIPT", { } ).items( ):
            for command in commands:
                self._rooms[room].addUserCommand( command, context )

        #consumeVal( props, "NAME", lambda name: self._rooms[room].setName ( name ) )
        self._rooms[room].setName ( props.pop ( "NAME", self._rooms[room].getName ( ) ) )

        # Deal with making exits.
        for (dest, keys) in props.pop( "LINKS", { } ).items( ):

            # Sometimes, every now and then... (rather implausibly, the only reason I did was for a
            # demonstration maze-y-thing) we might want to open two exits to the same room.  Of
            # course we can't have two keys in a dictionary with the same value, and YAML just
            # throws one of them out. So, I made another convention to remove underscores from the
            # name before use, so we could have multiple unique keys leading to the same room.
            dest = dest.replace("_", "")

            k = Link( room, dest, self )

            self._exits += [ k ]
            self._rooms[ room ].addExit( k )

            # If you don't actually care about setting exit messages just now, there should be a
            # concise way to just make an exit, without subproperties.
            if type( keys ) == str:

                k.setName( keys )

            else:

                # Otherwise, exits get their own properties, etc., like everything else.

                k.setName( keys.pop( "NAME", "[G]eneric [E]xit;exit;ge" ) )

                for ( context, commands ) in props.pop( "POSTSCRIPT", { } ).items( ):
                    for command in commands:
                        self._rooms[room].addUserCommand( command, context )

                for prop in keys:
                    k.setProp( prop, keys[prop] )

        # Set the remaining properties (which are ordinary properties) on the Room.
        for ( prop, val ) in props.items():

            if type ( val ) == str:
                self._rooms[room].setProp( prop, val.rstrip () )

    def elements ( self, targets = None ):

        """Return a list of elements (rooms and exits) matching 'targets': first all the rooms named
        in the list of targets, then all the exits attached to those rooms. If 'targets' is None,
        will return everything."""

        if not targets:
            return [ self._rooms[ rn ] for rn in self._rooms.keys( ) ] + self._exits

        rooms = []
        exits = []

        for target in targets:

            if target in self._rooms:
                rooms += [ self._rooms[ target ] ]
                exits += self._rooms[ target ].exits( )

        return rooms + exits

    def toCreate ( self, targets = None ):

        """Return list of the commands necessary to create and set up rooms and exits corresponding
        to 'targets' or, if 'targets' is None or a false value, the entire project. (See .elements()
        for what the targets are.)"""

        k = []

        for elem in self.elements( targets ):
            k += elem.build( )

        # We want to make sure we run user commands after /everything/ has been built.

        for elem in self.elements( targets ):
            k += elem.postProcess( )

        if not targets:
            # Only run the general custom build commands if we're building everything.
            k += self._buildPostscript

        return k

    def toUpdate ( self, targets = None ):

        """Return list of the commands necessary to create and set up rooms and exits corresponding
        to 'targets' or, if 'targets' is None or a false value, the entire project. (See .elements()
        for what the targets are.)"""

        k = [ ]

        for elem in self.elements( targets ):
            k += elem.realise( )

        return k

    def toDestroy ( self, targets = None ):

        """Return a list of MUCK commands necessary to recycle and unregister rooms and exits
        corresponding to 'targets', or the entire project if no targets specified."""

        k = [ ]

        for elem in self.elements( targets ):
            k += elem.remove( )

        for elem in self.elements( targets ):
            k += elem.postProcess( "DESTROY" )

        if not targets:
            k += self._destroyPostscript

        return k

    def toPostProcess ( self, targets = None ):

        """Return a command-list necessary to run all of the user's custom commands specified in
        POSTSCRIPT: directives. This is considered a separate operation because the effect of said
        commands isn't really known ahead of time, and so guessing whether the user might want them
        re-run, say, on .toUpdate( ), isn't necessarily the best idea."""

        k = [ ]

        for elem in self.elements( targets ):
            k += elem.postProcess( )

        return k

    def room ( self, name ):

        if name in self._rooms:
            return self._rooms[name]

        return None


def compileProject ( filename ):

    with open ( filename ) as yamlFile:

        parsed = yaml.load ( yamlFile )

        # These properties are set on all the rooms first, but can be overridden when it
        # comes time to set the room's own properties. They may be useful, for instance,
        # when using list-based @descs, or some other sort of repetitive thing.

        rooms = parsed["rooms"].copy( )

        our_globals = rooms.pop( "ALL", { } )

        project = Project( parsed["projectName"] )

        if "config" in parsed:

            for key in parsed["config"]:
                project.configure( key, parsed["config"][key] )

        for roomID in rooms.keys( ):

            # In the process of room creation, values are actually removed from the set of
            # properties being used. Normally this is not a problem, but in this case it can easily
            # result in some of our 'global' properties -- notably POSTSCRIPT: -- being not so
            # global. So, we make a copy for each invocation of applyProps( ). It has to be a "deep
            # copy", as values are also removed from child dicts.
            project.applyProps ( copy.deepcopy( our_globals ), roomID )

            project.applyProps ( rooms[roomID], roomID )

        if "POSTSCRIPT" in parsed:

            for ( context, commands ) in parsed[ "POSTSCRIPT" ].items( ):
                for command in commands:
                    project.addUserCommand( command, context )


        return project

def saveProject ( project ):

    """Write build instructions for project 'project' to text files in current directory."""

    # Of course, this might fail. But it seems unlikely. And hopefully the users will be
    # able to figure out what went wrong from the exception ... there probably SHOULD still
    # be more error handling here ... oh well.

    with open( project.name + "-build.txt", "w" ) as fh:

        fh.write( "\n".join( project.toCreate( None ) ) )
        fh.write( "\n\n" )
        fh.write( "\n".join( project.toPostProcess( None ) ) )

    with open( project.name + "-destroy.txt", "w" ) as fh:

        fh.write( "\n".join( project.toDestroy( None ) ) )

    print( "Files written (probably.)" )


if __name__ == "__main__":

    filename = None
    opts = [ ]

    if len( sys.argv ) <= 1:
        print ( """Usage:

python muckBuilder.py [-o[:room,room2,...]] [-o[:room,room2,...]] \\
    filename.yaml

     ... where -o[:room,room2,...] is one of the following options/operations:

-d produces commands that can be used to un-build the entire project or the
given selection of rooms and their attached exits;

-c produces commands that can be used to build the entire project or the given
selection of rooms (though if they have exits that wish to be linked to other
rooms that are not built on the server, those exits will not be linked);

-u produces commands that only reset the properties on the given list of rooms,
or for the entire project, not creating or deleting anything;

-p (re-)runs the commands in POSTSCRIPT: BUILD: directives;

-C produces commands that can be used to build the entire project, and commands
that can be used to destroy it, writing them to files with names derived from
the projectName; if no other operation / option is given, -C is the default.

If you request multiple operations you will receive the results of those
operations in order without any particular separator. Everything is written to
standard output.

""" )
        quit ( )

    for arg in sys.argv[1:]:

        if not re.match( "^-[cdupC]", arg ):

            # It's probably a filename.
            if not filename:
                filename = arg

            else:
                raise Exception( "Not going to do more than one file at a time." )
                # (That might be good to have later, though.)

        else:
            opts += [ arg ]

    if not filename:
        raise Exception( "No filename provided." )

    # I'm not quite sure if this should actually BE the default. Oh well.

    opts = opts or [ "-C" ]

    project = compileProject( filename )

    for opt in opts:

        opt = opt[1:]               # Cuts off the leading - character.

        targets = None

        if len( opt ) > 2 and opt[1] == ':':
            targets = opt[ 2: ].split( "," )        # [2:] cuts off first 2 chars, i.e. /[cdu]:/

        if opt[0] == "c":
            print ( "\n".join( project.toCreate( targets ) ) + "\n" )

        if opt[0] == "d":
            print ( "\n".join( project.toDestroy( targets ) ) + "\n" )

        if opt[0] == "u":
            print ( "\n".join( project.toUpdate( targets ) ) + "\n" )

        if opt[0] == "p":
            print ( "\n".join( project.toPostProcess( targets ) ) + "\n" )

        if opt[0] == "C":
            saveProject( project )
