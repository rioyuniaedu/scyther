#!/usr/bin/python
#
#	If.py
#
#	Objects and stuff for the intermediate format
#
class Message(object):
	def __cmp__(self,other):
		return cmp(str(self),str(other))

	def inTerms(self):
		return self

	def isVariable(self):
		return False

class Constant(Message):
	def __init__ (self,type,s,optprime=""):
		self.type = type
		self.prime = optprime
		self.str = s
	
	def __str__(self):
		return self.str + self.prime

	def __repr__(self):
		return str(self)

class Variable(Constant):
	def isVariable(self):
		return True

class PublicKey(Constant):
	pass

class Composed(Message):
	def __init__ (self,m1,m2):
		self.left = m1
		self.right = m2
	
	def __str__(self):
		return "(" + str(self.left) + "," + str(self.right) + ")"

	def inTerms(self):
		return self.left.inTerms() + self.right.inTerms()

class PublicCrypt(Message):
	def __init__ (self,key,message):
		self.key = key
		self.message = message

	def __str__(self):
		return "{" + str(self.message) + "}" + str(self.key) + " "

	def inTerms(self):
		return self.key.inTerms() + self.message.inTerms()


class SymmetricCrypt(PublicCrypt):
	pass

class XOR(Composed):
	def __str__(self):
		return str(self.left) + " xor " + str(self.right)


class MsgList(list):
	def inTerms(self):
		l = []
		for m in self:
			l = l + m.inTerms()

class Fact(list):
	def __repr__(self):
		return "Fact<" + list.__repr__(self) + ">"

	def getActor(self):
		return None

class GoalFact(Fact):
	def __repr__(self):
		return "Goal " + Fact.__repr__(self)

class PrincipalFact(Fact):
	def __init__(self,t):
		self.step = t[0]
		self.readnextfrom = t[1]
		self.actor = t[2]
		self.runknowledge = t[3]
		self.knowledge = t[4]
		self.bool = t[5]
		self.session = t[6]

	def __str__(self):
		res = "Principal Fact:"
		res += "\nStep         " + str(self.step)
		res += "\nReadNextFrom " + str(self.readnextfrom)
		res += "\nActor        " + str(self.actor)
		res += "\nRunKnowledge " + str(self.runknowledge)
		res += "\nKnowledge    " + str(self.knowledge)
		#res += "\nBool         " + str(self.bool)
		res += "\nSession      " + str(self.session)
		return res + "\n"

	def __repr__(self):
		return str(self)

	def getActor(self):
		return self.actor

class TimeFact(Fact):
	def __repr__(self):
		return "Time " + Fact.__repr__(self)

class MessageFact(Fact):
	def __init__(self,t):
		self.step = t[0]
		self.realsender = t[1]
		self.claimsender = t[2]
		self.recipient = t[3]
		self.message = t[4]
		self.session = t[5]

	def __str__(self):
		res = "Message Fact:"
		res += "\nStep         " + str(self.step)
		res += "\nRealSender   " + str(self.realsender)
		res += "\nClaimSender  " + str(self.claimsender)
		res += "\nRecipient    " + str(self.recipient)
		res += "\nMessage      " + str(self.message)
		res += "\nSession      " + str(self.session)
		return res + "\n"

	def __repr__(self):
		return str(self)

	def spdl(self):
		res = ""
		res += "(" + str(self.claimsender)
		res += "," + str(self.recipient)
		res += ", " + str(self.message)
		res += " )"
		return res

class State(list):
	def __repr__(self):
		return "State<" + list.__repr__(self) + ">"

class Label(object):
	def __init__(self, name, category):
		self.name = name
		self.category = category
	
	def __str__(self):
		return "lb=" + self.name + ",type=" + self.category

	def __repr__(self):
		return str(self)

class Rule(object):
	def __init__(self,left=[],right=[]):
		def sanitize(x):
			if x == None:
				return []
			elif type(x) != list:
				return [x]
			else:
				return x

		self.left = sanitize(left)
		self.right = sanitize(right)
		self.label = None
		self.actors = []
	
	def setLabel(self,label):
		self.label = label
	
	def __str__(self):
		res = "Rule:"
		if self.label != None:
			res += " (" + str(self.label) +")"
		res += "\n"
		if len(self.left) > 0:
			res += str(self.left) + "\n"
		if len(self.right) > 0:
			if len(self.left) > 0:
				res += "=>\n"
			res += str(self.right) + "\n"
		res += ".\n"
		return res

	def __repr__(self):
		return str(self)

	def getActors(self):
		return self.actors

	def getFacts(self):
		return self.left + self.right


class InitialRule(Rule):

	def __str__(self):
		return "Initial " + Rule.__str__(self)


class MessageRule(Rule):

	def __init__(self,left=[],right=[]):
		Rule.__init__(self,left,right)
		self.actors = []
		for fact in self.getFacts():
			actor = fact.getActor()
			if actor != None:
				self.actors.append(actor)

	def __str__(self):
		return "Message " + Rule.__str__(self)

class GoalRule(Rule):
	def __str__(self):
		return "Goal " + Rule.__str__(self)

class CorrespondenceRule(GoalRule):
	def __init__(self, l):
		GoalRule.__init__(self,l,None)
	
	def __str__(self):
		return "Correspondence " + GoalRule.__str__(self)

class SecrecyRule(GoalRule):
	def __init__(self, l):
		GoalRule.__init__(self,l,None)
	
	def __str__(self):
		return "Secrecy " + GoalRule.__str__(self)

class STSecrecyRule(GoalRule):
	def __init__(self, l):
		GoalRule.__init__(self,l,None)
	
	def __str__(self):
		return "Short-term Secrecy " + GoalRule.__str__(self)

class AuthenticateRule(GoalRule):
	def __init__(self, l):
		GoalRule.__init__(self,l,None)
	
	def __str__(self):
		return "Authenticate " + GoalRule.__str__(self)

class Protocol(list):
	def setFilename(self, filename):
		# TODO untested
		parts = filename.split("/")
		self.path = "".join(parts[:-1])
		self.filename = parts[-1]

	# Get head of filename (until first dot)
	def getBasename(self):
		parts = self.filename.split(".")
		if parts[0] == "":
			return "None"
		else:
			return parts[0]

	# Construct protocol name from filename
	def getName(self):
		return self.getBaseName()
		

