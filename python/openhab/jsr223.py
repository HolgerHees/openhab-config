import sys
import types

def get_scope():
    depth = 1
    while True:
        try:
            frame = sys._getframe(depth)
            name = str(type(frame.f_globals))
            if name == "<type 'scope'>":
                return frame.f_globals
            depth += 1
        except ValueError:
            raise EnvironmentError("No JSR223 scope is available")

def _get_scope_value(scope, name):
    return scope.get(name, None) or getattr(scope, name, None)

_presets = [
    [[ "SimpleRule" ], "RuleSimple"],
    [[ "automationManager" ], "RuleSupport"],
]

class _Jsr223ModuleFinder(object):
    class ScopeModule(types.ModuleType):        
        def __getattr__(self, name):
            global _presets
            scope = get_scope()
            if name == "scope":
                return scope
            value = _get_scope_value(scope, name)
            if value is None:
                for preset in _presets:
                    if name in preset[0]:
                        scriptExtension = _get_scope_value(scope, "scriptExtension")
                        # print "auto-import preset ", name, preset, scriptExtension
                        scriptExtension.importPreset(preset[1])
            return value if value is not None else _get_scope_value(scope, name)
    
    def load_module(self, fullname):
        if fullname not in sys.modules:
            m = _Jsr223ModuleFinder.ScopeModule('scope')
            setattr(m , '__file__', '<jsr223>')
            setattr(m , '__name__', 'scope')
            setattr(m , '__loader__', self)
            sys.modules[fullname] = m
                
    def find_module(self, fullname, path=None):
        if fullname == "openhab.jsr223.scope":
            return self
        
sys.meta_path.append(_Jsr223ModuleFinder())
 
def get_automation_manager():
    scope = get_scope()
    _get_scope_value(scope, "scriptExtension").importPreset("RuleSupport")
    automation_manager = _get_scope_value(scope, "automationManager")
    return automation_manager


