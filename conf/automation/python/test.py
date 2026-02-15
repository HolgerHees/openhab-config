import sys
import scope

def scriptUnloaded():
   print("I am logged third.")

def scriptLoaded(filename):
   print("I am logged second and I am from " + filename + ".")

scope.lifecycleTracker.addDisposeHook(lambda : print("I am logged fourth. Bye!"))

print("I am logged first.")


