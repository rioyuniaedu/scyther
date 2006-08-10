#!/usr/bin/python

#---------------------------------------------------------------------------

""" Import externals """
import wx
import os
import sys
import re
import threading
import StringIO

#---------------------------------------------------------------------------

""" Import scyther components """
import Scyther.XMLReader as XMLReader
import Scyther.Claim as Claim
import Scyther.Scyther as Scyther

""" Import scyther-gui components """
import Tempfile
import Preference
import Attackwindow
import Icon

#---------------------------------------------------------------------------
if Preference.usePIL():
    import Image
#---------------------------------------------------------------------------

class ScytherThread(threading.Thread):

    """ The reason this is a thread is because we might to decide to
    abort it. However, apparently Python has no good support for killing
    threads yet :( """

    # Override Thread's __init__ method to accept the parameters needed:
    def __init__ ( self, parent ):

        self.parent = parent
        parent.verified = False
        parent.claims = []

        threading.Thread.__init__ ( self )

    def run(self):

        self.claimResults()

        # Results are done (claimstatus can be reported)

        # Shoot down the verification window and let the RunScyther function handle the rest
        self.parent.verified = True
        self.parent.verifywin.Close()

    def claimResults(self):
        """ Convert spdl to result (using Scyther)
        """

        self.parent.scyther = scyther = Scyther.Scyther()
        scyther.options = self.parent.options
        scyther.setInput(self.parent.spdl)

        # verification start
        self.parent.claims = scyther.verify()

        self.parent.summary = str(scyther)

#---------------------------------------------------------------------------

class AttackThread(threading.Thread):

    """ This is a thread because it computes images from stuff in the
    background """

    # Override Thread's __init__ method to accept the parameters needed:
    def __init__ ( self, parent, resultwin, callbackclaim=None,callbackattack=None,callbackdone=None ):

        self.parent = parent
        self.resultwin = resultwin
        self.callbackclaim = callbackclaim
        self.callbackattack = callbackattack
        self.callbackdone = callbackdone
        self.totalattacks = 0
        for cl in self.parent.claims:
            for attack in cl.attacks:
                self.totalattacks += 1

        threading.Thread.__init__ ( self )

    def run(self):

        # create the images in the background
        # when the images of a claim are done, callback is called with
        # the claim
        self.makeImages()

    def makeImages(self):
        """ create images """
        done = 0
        for cl in self.parent.claims:
            for attack in cl.attacks:
                self.makeImage(attack)
                done += 1
                if self.callbackattack:
                    wx.CallAfter(self.callbackattack,attack,self.totalattacks,done)
            if self.callbackclaim:
                wx.CallAfter(self.callbackclaim,cl)
        if self.callbackdone:
            wx.CallAfter(self.callbackdone)

    def writeGraph(self,txt,fp):

        def graphLine(txt):
            fp.write("\t%s;\n" % (txt))

        def setAttr(EdgeNodeDefAll,atxt):
            if EdgeNodeDefAll == 3:
                setAttr(0,atxt)
                setAttr(1,atxt)
                setAttr(2,atxt)
            else:
                if EdgeNodeDefAll == 0:
                    edge = "edge"
                elif EdgeNodeDefAll == 1:
                    edge = "node"
                else:
                    graphLine("%s" % atxt)
                    return
                graphLine("%s [%s]" % (edge,atxt))

        def oldFontDefs(txt):
            """
            Old hack. Remove after windows recompile TODO
            """
            if txt.startswith("\tfontname"):
                return True
            if txt.startswith("\tfontsize"):
                return True
            if txt.startswith("\tnode [fontname"):
                return True
            if txt.startswith("\tnode [fontsize"):
                return True
            if txt.startswith("\tedge [fontname"):
                return True
            if txt.startswith("\tedge [fontsize"):
                return True
            return False

        for l in txt.splitlines():
            # hack to get rid of font defs
            # TODO remove this once new windows version is compiled
            if not oldFontDefs(l):
                fp.write(l)
                if l.startswith("digraph"):
                    # Write additional stuff for this graph
                    graphLine("dpi=96")
                    graphLine("rankdir=TB")
                    graphLine("nodesep=0.1")
                    graphLine("ranksep=0.001")
                    graphLine("mindist=0.1")
                    if sys.platform.startswith("lin"):
                        setAttr(3,"fontname=\"Sans\"")
                    else:
                        setAttr(3,"fontname=\"Arial\"")
                    setAttr(3,"fontsize=10")
                    setAttr(1,"height=\"0.01\"")
                    setAttr(1,"width=\"0.01\"")
                    setAttr(1,"margin=\"0.08,0.03\"")
                    #setAttr(0,"decorate=true")

    def makeImage(self,attack):
        """ create image for this particular attack """
        if Preference.usePIL():
            # If we have the PIL library, we can do postscript! great
            # stuff.
            type = "ps"
            ext = ".ps"
        else:
            # Ye olde pnge file
            type = "png"
            ext = ".png"

        # command to write to temporary file
        (fd2,fpname2) = Tempfile.tempcleaned(ext)
        f = os.fdopen(fd2,'w')

        cmd = "dot -T%s" % (type)

        # execute command
        cin,cout = os.popen2(cmd,'b')
    
        self.writeGraph(attack.scytherDot,cin)
        cin.close()

        for l in cout.read():
            f.write(l)

        cout.close()
        f.flush()
        f.close()

        # if this is done, store and report
        attack.filetype = type
        attack.file = fpname2  # this is where the file name is stored

#---------------------------------------------------------------------------

class VerificationWindow(wx.Dialog):
    def __init__(
            self, parent, title, pos=wx.DefaultPosition, size=wx.DefaultSize, 
            style=wx.DEFAULT_DIALOG_STYLE
            ):

        wx.Dialog.__init__(self,parent,-1,title,pos,size,style)

        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, -1, "Verifying protocol description")
        sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)

        btnsizer = wx.StdDialogButtonSizer()
        
        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.ALIGN_CENTER, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

#---------------------------------------------------------------------------

class ErrorWindow(wx.Dialog):
    def __init__(
            self, parent, title, pos=wx.DefaultPosition, size=wx.DefaultSize, 
            style=wx.DEFAULT_DIALOG_STYLE,errors=[]
            ):

        wx.Dialog.__init__(self,parent,-1,title,pos,size,style)

        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, -1, "Errors")
        sizer.Add(label, 0, wx.ALIGN_LEFT|wx.ALL, 5)

        line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)

        label = wx.StaticText(self, -1, "\n".join(errors))
        sizer.Add(label, 0, wx.ALIGN_LEFT|wx.ALL, 5)

        line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)

        btnsizer = wx.StdDialogButtonSizer()
        
        btn = wx.Button(self, wx.ID_OK)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.ALIGN_CENTER, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

#---------------------------------------------------------------------------

class ResultWindow(wx.Frame):

    """
    Displays the claims status and contains buttons to show the actual
    attack graphs

    TODO: this really should have a statusbar that works.

    TODO: on windows, it updates really slow, and the background is the
    wrong colour. Basically, it inhales air. Hard.
    """

    def __init__(
            self, parent, parentwindow, title, pos=wx.DefaultPosition, size=wx.DefaultSize, 
            style=wx.DEFAULT_DIALOG_STYLE
            ):

        wx.Frame.__init__(self,parentwindow,-1,title,pos,size,style)
	self.SetBackgroundColour('Default')
        Icon.ScytherIcon(self)

        self.parent = parent
        self.thread = None
        self.Bind(wx.EVT_CLOSE, self.onCloseWindow)

        self.CreateStatusBar()
        self.BuildTable()

    def onViewButton(self,evt):
        btn = evt.GetEventObject()
        w = Attackwindow.AttackWindow(btn.claim)
        w.Show(True)

    def onCloseWindow(self,evt):
        """ TODO we should kill self.thread """

        # Clean up
        self.parent.claims = None

        self.Destroy()

    def BuildTable(self):
        # Now continue with the normal construction of the dialog
        # contents

        # For these claims...
        claims = self.parent.claims

        # set up grid
        self.grid = grid = wx.GridBagSizer(0,0)
        #self.grid = grid = wx.GridBagSizer(7,1+len(claims))

        def titlebar(x,title,width=1):
            txt = wx.StaticText(self,-1,title)
            font = wx.Font(14,wx.NORMAL,wx.NORMAL,wx.BOLD)
            txt.SetFont(font)
            grid.Add(txt,(0,x),(1,width),wx.ALL,10)

        titlebar(0,"Claim",4)
        titlebar(4,"Status",2)
        titlebar(6,"Comments",1)

        self.lastprot = None
        self.lastrole = None
        views = 0
        for index in range(0,len(claims)):
            views += self.BuildClaim(grid,claims[index],index+1)

        if views > 0:
            titlebar(7,"Classes",1)

        self.SetSizer(grid)
        self.Fit()

    def BuildClaim(self,grid,cl,ypos):
        # a support function
        def addtxt(txt,column):
            grid.Add(wx.StaticText(self,-1,txt),(ypos,column),(1,1),wx.ALIGN_CENTER_VERTICAL|wx.ALL,10)

        n = len(cl.attacks)
        xpos = 0

        # protocol, role, label
        prot = str(cl.protocol)
        showP = False
        showR = False
        if prot != self.lastprot:
            self.lastprot = prot
            showP = True
            showR = True
        role = str(cl.role)
        if role != self.lastrole:
            self.lastrole = role
            showR = True
        if showP:
            addtxt(prot,xpos)
        if showR:
            addtxt(role,xpos+1)
        xpos += 2
        
        # claim id
        addtxt(str(cl.id),xpos)
        xpos += 1

        # claim parameters
        claimdetails = str(cl.claimtype)
        if cl.parameter:
            claimdetails += " %s" % (cl.parameter)
        addtxt(claimdetails + "  ",xpos)
        xpos += 1

        # button for ok/fail
        if None:
            # old style buttons (but they looked ugly on windows)
            tsize = (16,16)
            if cl.okay:
                bmp = wx.ArtProvider_GetBitmap(wx.ART_TICK_MARK,wx.ART_CMN_DIALOG,tsize)
            else:
                bmp = wx.ArtProvider_GetBitmap(wx.ART_CROSS_MARK,wx.ART_CMN_DIALOG,tsize)
            if not bmp.Ok():
                bmp = wx.EmptyBitmap(tsize)
            bmpfield = wx.StaticBitmap(self,-1,bmp)
            grid.Add(bmpfield,(ypos,xpos),(1,1),wx.ALIGN_CENTER_VERTICAL|wx.ALL,10)
        else:
            # new style text control Ok/Fail
            rank = cl.getRank()
            rankt = [('Fail','red'),
                     ('Fail','dark red'),
                     ('Ok','dark green'),
                     ('Ok','forest green')]
            txt = wx.StaticText(self,-1,rankt[rank][0])
            font = wx.Font(11,wx.NORMAL,wx.NORMAL,wx.BOLD)
            txt.SetFont(font)
            txt.SetForegroundColour(rankt[rank][1])
            grid.Add(txt,(ypos,xpos),(1,1),wx.ALL,10)
        xpos += 1

        # verified?
        vt = cl.getVerified()
        if vt:
            addtxt(vt,xpos)
        xpos += 1

        # remark something 
        addtxt(cl.getComment(),xpos)
        xpos += 1
                
        # add view button (enabled later if needed)
        if n > 0:
            cl.button = wx.Button(self,-1,"%i %s" % (n,cl.stateName(n)))
            cl.button.claim = cl
            grid.Add(cl.button,(ypos,xpos),(1,1),wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
            cl.button.Disable()
            if n > 0:
                # Aha, something to show
                self.Bind(wx.EVT_BUTTON, self.onViewButton,cl.button)
        else:
            cl.button = None
        xpos += 1

        # Return 1 if there is a view possible
        if n > 0:
            return 1
        else:
            return 0


#---------------------------------------------------------------------------


class ScytherRun(object):
    def __init__(self,mainwin,mode):

        self.mainwin = mainwin
        self.mode = mode
        self.spdl = mainwin.control.GetValue()

        # Verification window

        self.verifywin = verifywin = VerificationWindow(mainwin,"Running Scyther %s process" % mode)
        verifywin.Center()
        verifywin.Show(True)

        # start the thread
        
        self.options = mainwin.settings.ScytherArguments(mode)
        self.verified = False
        verifywin.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))

        t = ScytherThread(self)
        t.start()

        # start the window and show until something happens
        # if it terminates, this is a cancel, and should also kill the thread. (what happens to a spawned Scyther in that case?)
        # if the thread terminames, it should close the window normally, and we end up here as well.
        val = verifywin.ShowModal()

        if self.verified:
            # Scyther program is done (the alternative is that it was
            # cancelled)
            if self.scyther.errorcount == 0:
                # Great, we verified stuff, progress to the claim report
                title = "Scyther results : %s" % mode
                self.resultwin = resultwin = ResultWindow(self,mainwin,title)

                def attackDone(attack,total,done):
                    if resultwin:
                        txt = "Generating attack graphs (%i of %i done)." % (done,total)
                        resultwin.SetStatusText(txt)
                        #resultwin.Refresh()

                def claimDone(claim):
                    if resultwin:
                        if claim.button and len(claim.attacks) > 0:
                            claim.button.Enable()

                def allDone():
                    if resultwin:
                        resultwin.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
                        resultwin.SetStatusText("Done.")

                resultwin.Center()
                resultwin.Show(True)
                resultwin.SetCursor(wx.StockCursor(wx.CURSOR_ARROWWAIT))

                wx.Yield()

                t = AttackThread(self,resultwin,claimDone,attackDone,allDone)
                t.start()

                resultwin.thread = t

            else:
                # Darn, some errors. report.
                title = "Scyther errors : %s" % mode
                errorwin = ErrorWindow(mainwin,title,errors=self.scyther.errors)
                errorwin.Center()
                val = errorwin.ShowModal()



#---------------------------------------------------------------------------



