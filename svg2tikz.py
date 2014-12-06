#!/usr/bin/env python
""" A program to generate TiKZ code from simple SVGs 
"""
# (c) 2014 by Pedro A. Aranda Gutierrez; paaguti@hotmail.com
# released under LGPL 3.0
# see LICENSE

from __future__ import print_function
from lxml import etree
import sys
import re

class TiKZMaker(object):
    _output     = None
    _unit       = "mm"
    _standalone = True
    _debug      = False

    align     = re.compile(r"text-align:([^;]+);")
    ffamily   = re.compile(r"font-family:([^;]+);")
    fsize     = re.compile(r"font-size:(\d+(\.\d+)?)px;")
    # translate = re.compile(r"translate\((-?\d+(\.\d+)?([eE]-?\d+)?),(-?\d+(\.\d+)?([eE]-?\d+)?)\)")
    stroke    = re.compile(r"stroke:#(none|[0-9a-f]{6});")
    fill      = re.compile(r"fill:#(none|[0-9a-f]{6});")

    def __init__(self, output=sys.stdout, standalone = False,debug=False,unit="mm"):
        self._output     = output
        self._unit       = unit
        self._standalone = standalone
        self._debug      = debug
        
    def str2u(self,s):
        f = float(s) if not isinstance(s,float) else s
        return "%.1f%s" % (f,self._unit)

    def u2str(self,x):
        return "(%s)" % self.str2u(x)

    def pt2str(self,x,y,sep=','):
        return "(%s%s%s)" % (self.str2u(x),sep,self.str2u(y))
    
    def addNS(self,tag,defNS="{http://www.w3.org/2000/svg}"):
        return defNS+tag

    namedTagRe = re.compile(r"\{[^}]+\}(.*)")

    def delNS(self,tag):
        # if self._debug:
        #     print ("Full tag : '%s'" % tag,file=sys.stderr)
        m = TiKZMaker.namedTagRe.match(tag)
        # if self._debug:
        #     print (m.groups(),file=sys.stderr)
        return m.group(1)

    def get_loc(self,elem):
        # print (elem.tag,elem.attrib)
        x = float(elem.attrib['x'])
        y = float(elem.attrib['y'])
        return x,y

    def get_dim(self,elem):
        # print (elem.tag,elem.attrib)
        w = float(elem.attrib['width'])
        h = float(elem.attrib['height'])
        return w,h

    def hex2rgb(self,colour):
        r = int("0x"+colour[0:2],0)
        g = int("0x"+colour[2:4],0)
        b = int("0x"+colour[4:],0)
        return r,g,b

    def style2colour(self,style):
        if self._debug: print ("style2colour(%s)" % style,file=sys.stderr)
        result = []
        m = TiKZMaker.stroke.findall(style)
        # print ("m = %s" % m,file=sys.stderr)
        try:
            colour=m[0]
            if colour == "none":
                result.append("draw=none")
            else:
                print ("\\definecolor{dc}{RGB}{%d,%d,%d}" % self.hex2rgb(colour),file=self._output)
                result.append("draw=dc")
        except: pass
        m = TiKZMaker.fill.findall(style)
        try:
            colour=m[0]
            if colour == "none":
                result.append("fill=none")
            else:
                # print ("m = %s" % colour,file=sys.stderr)
                print ("\\definecolor{fc}{RGB}{%d,%d,%d}" % self.hex2rgb(colour),file=self._output)
                result.append("fill=fc")
        except: pass
        if len(result) == 0: return ""
        return "[%s]" % ",".join(result)

    def process_rect(self,elem):
        x,y   = self.get_loc(elem)
        w,h   = self.get_dim(elem)
        style = self.style2colour(elem.attrib['style'])
        print ("\\draw %s %s rectangle %s ;" % (style,self.pt2str(x,y),self.pt2str(w+x,h+y)),
               file=self._output)

    def process_circle(self,elem):
        x    = float(elem.attrib['cx'])
        y    = float(elem.attrib['cy'])
        r    = float(elem.attrib['r'])
        style = elem.attrib['style']
        print ("\\draw %s circle %s ;" % (self.pt2str(x,y),self.u2str(r)),
               file=self._output)

    def process_ellipse(self,elem):
        x    = float(elem.attrib['cx'])
        y    = float(elem.attrib['cy'])
        rx   = float(elem.attrib['rx'])
        ry   = float(elem.attrib['ry'])
        style = elem.attrib['style']
        print ("\\draw %s ellipse %s ;" % (self.pt2str(x,y),self.pt2str(rx,ry,' and ')),
               file=self._output)

    dimRe  = re.compile(r"(-?\d+(\.\d+)?),(-?\d+(\.\d+)?)(\s+(\S.*))?")

    def dimChop(self,s):
        m=TiKZMaker.dimRe.match(s)
        x=float(m.group(1))
        y=float(m.group(3))
        return self.pt2str(x,y),m.group(6),x,y

    pathRe = re.compile(r"(([cCqQlLmM] )?(-?\d+(\.\d+)?),(-?\d+(\.\d+)?))(\s+(\S.*))?")

    def path_chop(self,d,first,incremental):
        def path_controls(inc,p1,p2,p3):
            print (".. controls %s%s and %s%s .. %s%s" % (inc,p1,inc,p2,inc,p3),file=self._output)
            
        # print (" -->> %s" % d,file=sys.stderr)
        # print (d,file=sys.stderr)
        if d == 'z':
            print ("-- cycle",file=self._output)
            return None, False, False            
        m = TiKZMaker.pathRe.match(d)
        # print (m,file=sys.stderr)
        # print (m.groups(),file=sys.stderr)
        spec = m.group(2)
        x1 = float(m.group(3))
        y1 = float(m.group(5))
        pt = self.pt2str(x1,y1)
        
        if spec is not None:
            incremental = spec[0] != spec[0].upper()
        inc = "++" if incremental else ""
            
        rest = m.group(8)
        # print (" --]]>> [%s|%s]" % (spec,rest),file=sys.stderr)

        spec = spec[0] if spec is not None else None

        if spec in ["c", "C"]:
            pt2,rest,x2,y2 = self.dimChop(rest)
            pt3,rest,x3,y3 = self.dimChop(rest)
            #
            # Quick hack
            #
            # %.. controls ++(4.2mm,4.2mm) and ++(12.6mm,-4.2mm) .. ++(16.9mm,0.0mm)
            # Correct
            # .. controls ++(4.2mm,4.2mm) and ++(-4.2mm,-4.2mm) .. ++(16.8mm,0.0mm)
            if incremental:
                pt2 = self.pt2str(x2-x3,y2-y3)
            else:
                print ("** Warning: check controls",file=sys.stderr)
                print ("%%%% Warning: check controls",file=self._output)
            path_controls (inc,pt,pt2,pt3)
        elif spec in ["Q","q"]:
            print (">> Decoding quadratic Bezier curve",file=sys.stderr)
            pt2,rest,x2,y2 = self.dimChop(rest)
            if spec == "Q":
                print ("%% Warning: ignoring (abs) Quadratic Bezier",file=sys.stderr)
                print ("%% This should be a quadratic Bezier with control point at %s" % pt,file=self._output)
                print (" -- %s" % (pt2),file=self._output)
            else:
                #
                # See http://www.latex-community.org/forum/viewtopic.php?t=4424&f=45
                # And above
                #
                # Q3 = P2
                # Q2 = (2*P1+P2)/3 [ -P2 ^above^]
                # Q1 = 
                pt3 = pt2
                pt2 = self.pt2str(2.0*(x1-x2)/3.0,2.0*(y1-y2)/3)
                pt1 = self.pt2str(2.0*x1/3.0,      2.0*y1/3)
                path_controls(inc,pt1,pt2,pt3)
        elif spec in [ "M","m"]:
            if first is False: print(";",file=self._output)
            print("\\draw %s%s" % (inc,pt),file=self._output)
        elif spec in ["L","l"] or spec is None:
            print ("-- %s%s" % (inc,pt),file=self._output)
        return rest,False,incremental
    
    def process_path(self,elem):
        d = elem.attrib['d']
        f = True
        i = False
        while d is not None and len(d) > 0:
            d,f,i = self.path_chop(d,f,i)
        print (";",file=self._output)

    def get_align(self,style):
        m = TiKZMaker.align.findall(style)
        try:
            al = {'start':'left','center':'center','end':'right' }[m[0]]
        except:
            al = "center"
        if al != "center":
            print ("** Warning: ignored string alignment to the %s" % al,file=sys.stderr)
            print ("%%%% This element will be anyhow centered!",file=self._output)
        return "align=%s" % al

    def get_font(self,style):

        fnames = {
            "serif" :      "",
            "Serif" :      "",
            "sans-serif" : "\\sffamily",
            "Sans" :       "\\sffamily",
        }
    
        result = []
        size = 0.0
        fn = None
        try:
            ssize,_ = TiKZMaker.fsize.findall(style)[0]
            size = float(ssize)
            if size <= 4.0 : result.append("\\small")
            elif size <= 6.0: pass
            else: result.append("\\large")
        except: pass
        try:
            fn = TiKZMaker.ffamily.findall(style)[0]
            if fn in fnames:
                if len(fnames[fn]):
                    result.append(fnames[fn])
        except: pass
        if self._debug:
            print (">> %s" % style,file=sys.stderr)
            print ("** Font %s %.1f => %s" % (fn,size,result),file=sys.stderr)
        return "font=%s" % "".join(result) if len(result) != 0 else None

    def process_tspan(self,elem,x,y,style):
        txt = elem.text
        try:
            x,y = self.get_loc(elem)
        except: pass
        try:
            style=elem.attrib['style']            
        except: pass
        styles = [self.get_align(style)]
        f = self.get_font(style)
        if f is not None: styles.append(f)
        print ("\\node [%s] at %s { %s };" % (",".join(styles),self.pt2str(x,y),txt),
               file=self._output)
        
    def process_text(self,elem):
        x,y   = self.get_loc(elem)
        txt   = elem.text
        style = elem.attrib['style']
        if txt is None:
            for tspan in elem.findall(self.addNS('tspan')):
                self.process_tspan(tspan,x,y,style)
        else:
            self.process_tspan(elem,x,y,style)

    transformRe = re.compile(r"(translate|rotate|matrix)\(([^)]+)\)")
    floatRe     = re.compile(r"(-?\d+(\.\d+([eE]-?\d+)?)?)")

    def transform2scope(self,elem):
        # print ("transform2scope(%s)" % elem.attrib,file=sys.stderr)
        try:
            transform = elem.attrib['transform']
            if self._debug: 
                print (transform,file=sys.stderr)
            m = TiKZMaker.transformRe.match(transform)
            if self._debug: 
                print (m.groups(),file=sys.stderr)
            getFloats = TiKZMaker.floatRe.findall(m.group(2)) 
            if self._debug:
                print (getFloats,file=sys.stderr)
            nums = [ n for n,d,e in getFloats ]
            if self._debug: 
                print (nums,file=sys.stderr)
            xform = []

            if m.group(1) == "translate":
                xform.append("shift={(%s,%s)}" % (self.str2u(nums[0]),self.str2u(nums[1])))
            elif m.group(1) == "rotate":
                xform.append("rotate=%s" % nums[0])
            elif m.group(1) == "matrix":
                xform.append("cm={%s,%s,%s,%s,(%s,%s)}" % (nums[0],nums[1],nums[2],nums[3],
                                                           self.str2u(nums[4]),self.str2u(nums[5])))
            if len(xform) > 0:
                print ("\\begin{scope}[%s]" % ",".join(xform),file=self._output)
                return True
            return False
        except:
            return False

            
    def process_g(self,elem):
        if len([c for c in elem]) == 0: return
        xlate = {
            'g':       lambda e: self.process_g(e),
            'text':    lambda e: self.process_text(e),
            'rect':    lambda e: self.process_rect(e),
            'circle':  lambda e: self.process_circle(e),
            'ellipse': lambda e: self.process_ellipse(e),
            'path':    lambda e: self.process_path(e)
        }

        # print ("process_g(%s)" % elem.tag,file=sys.stderr)
        # print (" %d children" % len([c for c in elem]))
        for child in elem:
            for x in xlate:
                if self.delNS(child.tag) == x:
                    transform = self.transform2scope(child)
                    xlate[x](child)
                    if transform: print ("\\end{scope}",file=self._output)

    def mkTikz(self,svg):
        units = self._unit
        if self._standalone:
            print ("""\\documentclass[tikz,border=1mm]{standalone}
\\usepackage{tikz}
\\usetikzlibrary{shapes}
\\makeatletter
\\begin{document}""",file=self._output)

        print ("""\\begin{tikzpicture}
\\begin{scope}[yscale=-1]""",file=self._output)
        if self._debug:
            print (svg.getroot().attrib,file=sys.stderr)
        for elem in svg.getroot():
            if self.delNS(elem.tag) == 'g':
                if len([c for c in elem]) > 0:
                    transform=self.transform2scope(elem)
                    self.process_g(elem)
                    if transform: print ("\\end{scope}",file=self._output)
            elif self.delNS(elem.tag) == "namedview":
                try:
                    self._unit = elem.attrib["units"]
                except: 
                    self._unit = units

        print ("""\\end{scope}
\\end{tikzpicture}""",file=self._output)
        if self._standalone:
            print ("\\end{document}",file=self._output)
        self._unit = units

def main():
    import optparse
    parser = optparse.OptionParser(description=__doc__,
                                   usage="%prog [flags] file...")
    parser.add_option("-d","--debug",      dest="debug",      
                      action = "store_true", default=False, 
                      help="Enable debugging messages")
    parser.add_option("-o","--output",     dest="output",
                      default=None,  
                      help="Write to file(default is stdout)")
    parser.add_option("-s","--standalone", dest="standalone", 
                      action = "store_true", default=False, 
                      help="Make a standalone LaTEX file")
    
    options, remainder = parser.parse_args()
    processor = TiKZMaker(sys.stdout if options.output is None else open(options.output,"w"),
                          standalone=options.standalone, 
                          debug=options.debug)
    try:
        processor.mkTikz(etree.parse(remainder[0]))
    except IndexError:
        parser.print_help()
if __name__ == "__main__":
   main()
