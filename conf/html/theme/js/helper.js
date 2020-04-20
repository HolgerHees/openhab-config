var mvInitializer = function(){
    
    var BASE_DOMAIN = document.cookie.split( ';' ).map( function( x ) { return x.trim().split( '=' ); } ).reduce( function( a, b ) { a[ b[ 0 ] ] = b[ 1 ]; return a; }, {} )[ "base_domain" ];

    var authType = "";
    var domain = location.host;
    if( BASE_DOMAIN && domain != BASE_DOMAIN ) 
    {
        var parts = domain.split(".");
        var subDomain = parts.shift();
        if( subDomain.indexOf("fa") === 0 ) authType = "fa.";
        
        domain = parts.join(".");
    }
                        
    if(typeof angular === "undefined")
    {
        setTimeout(mvInitializer, 50);
        return;
    }

    var app = angular.module('app', []);

    var MV = {
        'handleClassArray': function( add, name, classList )
        {
            var index = classList.indexOf(name);
                                    
            if( add )
            {
                if( index == -1 ) classList.push(name);    
            }
            else
            {
                delete classList[index];    
            }
        },
        'handleClassList': function( add, name, classList )
        {
            if( add )
            {
                classList.add(name);
            }
            else
            {
                classList.remove(name);
            }
        },
        'getCurrentMillies': function()
        {
            let d = new Date();
            return d.getTime() * 1000 + d.getMilliseconds();
        }
    };

    (function() {
        'use strict';

        app.service('mvService', MVService);
        
        // angular.element(document.body).injector().get("mvService").refresh()
        
        MVService.$inject = ['OHService'];
        function MVService(OHService)
        {
            var vm = this;
            
            vm.refreshListener = [];
            vm.lastRefresh = -1;
            
            vm.refresh = refresh;
            vm.addRefreshListener = addRefreshListener;
            vm.removeRefreshListener = removeRefreshListener;
            vm.hasMissedReload = hasMissedReload;
            
            function refresh()
            {
                //console.log("mvService: call refresh");
                OHService.reloadItems();
                for( var i = 0; i < vm.refreshListener.length; i++ )
                {
                    //console.log("mvService: call refresh listener");
                    vm.refreshListener[i]();	
                }
            }

            function addRefreshListener( listener )
            {
                //console.log("mvService: register refresh listener");
                
                vm.refreshListener.push( listener );
            }
            
            function removeRefreshListener( listener )
            {
                var index = vm.refreshListener.indexOf(listener);
                if( index != -1 )
                {
                    //console.log("mvService: remove refresh listener " + index );
                    vm.refreshListener.splice(index,1);
                }
            }
            
            function hasMissedReload()
            {
                if( vm.lastRefresh == -1 ) return OHService.getItems() != undefined;
                
                // not older then 500ms
                return MV.getCurrentMillies() - vm.lastRefresh < 500;
            }
            
            let reloadItems = OHService.reloadItems;
            OHService.reloadItems = function()
            {
                //console.log("reloadItems");

                vm.lastRefresh = MV.getCurrentMillies();
                
                reloadItems();
            }

            /*let loadItems = OHService.loadItems;
            OHService.loadItems = function()
            {
                //console.log("loadItems");
                
                vm.lastRefresh = MV.getCurrentMillies();
                
                loadItems();
            }*/
        }
    })();







    /*****************************
    *                           *
    * CUSTOM WATCHER DIRECTIVES *
    *                           *
    *****************************/

    (function() {
        'use strict';

        app.directive("mvWatch", mvWatchLinker);
        
        mvWatchLinker.$inject = ['$rootScope'];
        function mvWatchLinker($rootScope) 
        {
            function isItemUsed( scope, itemName, expression, checkVars, myVars )
            {
                if( itemName == null || expression.indexOf(itemName) != -1 )
                {
                    return true;
                }
                
                if( checkVars )
                {
                    for( var name in myVars )
                    {
                        if( expression.indexOf(name) != -1 )
                        {
                            return true;
                        }
                    }
                }
                
                return false;
            }
            
            return {
                restrict: 'A',
                link: function(scope, element, attrs) 
                {
                    let myVars = {};
                    
                    //console.log(scope.ngModel.customwidget);
                    //console.log($rootScope.customwidgets[scope.ngModel.customwidget]);
                    if( $rootScope.customwidgets[scope.ngModel.customwidget].settings != undefined )
                    {
                        for( var config of $rootScope.customwidgets[scope.ngModel.customwidget].settings )
                        {
                            if( config['type'] != 'item' ) continue;
                            
                            //console.log( scope.ngModel.config[ config['id'] ] );
                            if( attrs.mvVars != undefined ) attrs.mvVars = attrs.mvVars.replace('config.' + config['id'], "'" + scope.ngModel.config[ config['id'] ] + "'" );
                            if( attrs.mvIf != undefined ) attrs.mvIf = attrs.mvIf.replace('config.' + config['id'], "'" + scope.ngModel.config[ config['id'] ] + "'" );
                            if( attrs.mvContent != undefined ) attrs.mvContent = attrs.mvContent.replace('config.' + config['id'], "'" + scope.ngModel.config[ config['id'] ] + "'" );
                            if( attrs.mvClass != undefined ) attrs.mvClass = attrs.mvClass.replace('config.' + config['id'], "'" + scope.ngModel.config[ config['id'] ] + "'" );
                        }
                    }
                    
                    if( attrs.mvClick != undefined )
                    {
                        element[0].addEventListener('click', function(event) { scope.$eval(attrs.mvClick,myVars); });
                    }
                                    
                    scope.$$postDigest(function()
                    {
                        scope.addUpdateListener(function( updatedItemName )
                        {
                            //console.log(updatedItemName);

                            let checkVars = false;
                            if( attrs.mvVars != undefined && isItemUsed( scope, updatedItemName, attrs.mvVars, checkVars, myVars ) )
                            {
                                myVars = scope.$eval(attrs.mvVars);
                                checkVars = true;
                            }
                            
                            if( attrs.mvIf != undefined && isItemUsed( scope, updatedItemName, attrs.mvIf, checkVars, myVars ) )
                            {
                                let display = scope.$eval(attrs.mvIf,myVars);
                                element[0].style="display:" + (display ? '' : 'none');
                            }
                            
                            if( attrs.mvContent != undefined && isItemUsed( scope, updatedItemName, attrs.mvContent, checkVars, myVars ) )
                            {
                                let content = scope.$eval(attrs.mvContent,myVars);
                                element[0].innerText=content;
                            }

                            if( attrs.mvClass != undefined && isItemUsed( scope, updatedItemName, attrs.mvClass, checkVars, myVars ) )
                            {
                                var mvClass = scope.$eval(attrs.mvClass,myVars);

                                //console.log(mvClass);
                                if( Array.isArray(mvClass) ) mvClass = mvClass[1];
                                
                                var className = element[0].getAttribute("class");
                                var classList = className == null ? [] : className.split(" ");
                                
                                for (var key in mvClass)
                                {
                                    MV.handleClassArray( mvClass[key], key, classList );
                                }
                                
                                var newClassName = classList.join(" ");
                                if( newClassName != className ) element[0].setAttribute("class", newClassName );
                            }
                        });
                    });
                }
            }
        }
    })();

    (function() {
        'use strict';
        
        app.directive("mvClassWatch", mvClassWatchLinker);
        
        function mvClassWatchLinker() {
            
            function checkReferencedElements( element, related_local_classes, mvClass )
            {
                // {'active':{'light_terasse':'active'},'auto':{'light_terasse':'auto'}}
                // {'active':{'light_garage_streedside':'active','light_frontdoor':'active'},'auto':{'light_garage_streedside':'auto','light_frontdoor':'auto'}}
                
                var className = element[0].getAttribute("class");
                var classList = className == null ? [] : className.split(" ");
                                
                for( var local_class of related_local_classes )
                {
                    var ref = mvClass[local_class];	
                    
                    var isActive = false;
                    for( var ref_element_id in ref )
                    {
                        var ref_element = document.querySelector("#"+ref_element_id);
                        var ref_class = ref[ref_element_id];
                        
                        if( ref_element.classList.contains( ref_class ) )
                        {
                            isActive = true;
                            break;
                        }
                    }
                    
                    MV.handleClassArray( isActive, local_class, classList );
                }
                
                var newClassName = classList.join(" ");
                if( newClassName != className ) element[0].setAttribute("class", newClassName );
            }
            
            function createObserver( ref_element, element, related_local_classes, mvClass )
            {
                var observer = new MutationObserver(function(mutationsList)
                {
                    for(var mutation of mutationsList) 
                    {
                        if( mutation.attributeName == 'class' )
                        {
                            checkReferencedElements( element, related_local_classes, mvClass );
                            break;
                        }
                    }
                });

                // Start observing the target node for configured mutations
                observer.observe(ref_element, { attributes: true, attributeOldValue: true });
                
                return observer;
            }
            
            return {
                restrict: 'A',
                link: function(scope, element, attrs) {
                    //console.log("init " + attrs.mvClasses);
                    var mvClass = scope.$eval(attrs.mvClasses);

                    let observer_r = [];
                    
                    let observed_elements = {};
                    
                    
                    for (var local_class in mvClass)
                    {
                        var ref = mvClass[local_class];

                        for( var ref_element_id in ref )
                        {
                            if( observed_elements[ ref_element_id ] == undefined ) observed_elements[ ref_element_id ] = [];

                            observed_elements[ ref_element_id ].push( local_class );					
                        }
                    }
                    
                    for( ref_element_id in observed_elements )
                    {
                        var ref_element = document.querySelector("#"+ref_element_id);
                        
                        var observer = createObserver( ref_element, element, observed_elements[ ref_element_id ], mvClass );

                        observer_r.push(observer);
                    }
                    
                    //console.log(observed_elements);
                    
                    scope.$on('$destroy', function (event) 
                    {
                        for(var i=0;i<observer_r.length;i++)
                        {
                            observer_r[i].disconnect();
                        }
                    });
                }
            }
        }
    })();

    (function() {
        'use strict';
        
        app.directive("mvTrigger", ["OHService","mvService","$rootScope", function (OHService,mvService,$rootScope)
        {
            function collectItem(scope,name)
            {
                if( scope.vm.watchedItems[name] == undefined ) scope.vm.watchedItems[name] = true;
            }
            
            function updateItem(scope,item)
            {
                let state = item.state
                let transformedState = item.transformedState ? item.transformedState : item.state
                
                // remove units like °C
                if( item.type.indexOf(":") != -1 )
                {
                    state = state.substr(0,state.indexOf(" "))
                    transformedState = transformedState.substr(0,transformedState.indexOf(" "))
                }
                scope.vm.watchedValues[item.name] = ( item == null ? [ 'N/A', 'N/A' ] : [ state, transformedState ] );
            }
            
            function triggerListener(scope,item)
            {
                for(var i=0;i<scope.vm.updateListener.length;i++)
                {
                    scope.vm.updateListener[i]( item == null ? null : item.name );
                }
            }
            
            return {
                restrict: "A",
                link: function mvTriggerLink(scope, elem, attrs)
                {
                    //console.log(elem);
                    
                    scope.vm = {};
                    scope.vm.$$watchers = scope.$$watchers;
                    
                    scope.vm.watchedItems = {};
                    scope.vm.watchedValues = {};
                    scope.vm.watchedGroups = {};
                    scope.vm.updateListener = [];
                    
                    //console.log(scope.$$watchers);
                    /*scope.$watch(function(){},function(newValue,oldValue)
                    {
                        console.log("watcher");
                    });*/
                    
                    // Disable watchers. We will enable them again on first opUdate round
                    scope.$$postDigest(function(){ scope.$$watchers = []; });

                    // Overwrite itemState function to catch all item usages
                    // additionally we can handle cached data for cases where we are not able to prevent digest cycles
                    scope.itemState = function ( name, ignoreTransform ) 
                    {
                        if( scope.vm.watchedValues[ name ] == undefined )
                        {
                            // Collect used items
                            collectItem(scope,name);

                            var item = OHService.getItem(name);
                            if( item == null ) 
                            {
                                // Should never happen
                                console.error("Item state requested before items initialized");
                                return null;
                            }

                            updateItem(scope,item);
                            //console.log("fetch state: " + name);
                        }
                        else
                        {
                            //console.log("reuse state: " + name);
                        }
                        
                        return scope.vm.watchedValues[ name ][ ignoreTransform ? 0 : 1 ];                
                    }
                    scope.itemValue = scope.itemState;
                    
                    scope.orgGetItem = scope.getItem ;
                    scope.getItem = function ( name ) 
                    {
                        // Collect used items
                        collectItem(scope,name);

                        var item = scope.orgGetItem( name );

                        if( typeof item == 'string' )
                        {
                            // Should never happen
                            console.error("Item requested before items initialized");
                            return null;
                        }

                        return item;
                    }
                    
                    scope.orgItemsInGroup = scope.itemsInGroup ;
                    scope.itemsInGroup = function ( name ) 
                    {
                        let items = scope.orgItemsInGroup(name);
                        if( scope.vm.watchedGroups[name] == undefined )
                        {
                            // Collect used items and transformed flag
                            for(var i=0;i<items.length;i++)
                            {
                                //console.log("collect item: " + items[i].name);
                                collectItem(scope,items[i].name);
                            }
                            
                            scope.vm.watchedGroups[name] = true;
                        }
                        
                        return items;                
                    }
                    
                    scope.addUpdateListener = function(callback)
                    {
                        scope.vm.updateListener.push(callback);
                    }

                    //console.log("mvTrigger: register");
                    
                    //window.setTimeout(function(){
                    //    let testItem = {name: "Temperature_FF_Livingroom", state: "20.0"};
                    //    $rootScope.$emit('openhab-update',testItem);
                    //},2000);
                    
                    // Register for OpenHab Item updates
                    OHService.onUpdate(scope, '', function (event, item)
                    {
                        /*var count = 0;
                        for (var k in scope.vm.watchedItems) {
                            if (scope.vm.watchedItems.hasOwnProperty(k)) {
                                ++count;
                            }
                        }*/
                        //console.log(scope.vm.watchedItems);
                        
                        //console.log("mvTrigger: onUpdate " + (item==null? "all" : item.name)  );
                        
                        // Specific items are only allowed if we are watching it
                        if( item != null && scope.vm.watchedItems[item.name] == undefined )
                        {
                            return;
                        }
                        
                        // reset all items
                        if( item == null )
                        {
                            scope.vm.watchedValues = {};
                        }
                        // reset specific item
                        else
                        {
                            updateItem(scope,item);
                        }

                        // notify listener about changes
                        triggerListener(scope,item);
                        
                        // restore $$watchers to allow the digest process to update the whole subtree
                        scope.$$watchers = scope.vm.$$watchers;
                        // remove $$watchers after finishing the digest to prevent later digest updates
                        scope.$$postDigest(function(){ scope.$$watchers = []; });
                    });
                    
                    scope.$on('$destroy', function()
                    {
                        scope.vm.updateListener = [];
                    });

                    if( mvService.hasMissedReload() )
                    {
                        console.log("Emit update event again, because mvTrigger missed initial update event");
                        mvService.lastRefresh = MV.getCurrentMillies();

                        // trigger 'openhab-update' event after the main thread has finished the initialisation
                        window.setTimeout(function()
                        {
                            $rootScope.$emit('openhab-update');
                            //OHService.reloadItems();
                        },0);
                    }
                }
            }
        }]);
    })();







    /*****************************
    *                           *
    *  CUSTOM GENERIC WIDGETS   *
    *                           *
    *****************************/

    (function() {
        'use strict';

        app.directive("mvSwitch", mvSwitchLinker);
        
        function mvSwitchLinker() {
            return {
                restrict: "A",
                link: function (scope, elem, attrs) 
                {
                    let itemName = scope.ngModel.config.item;

                    elem[0].querySelector('.widgetTitle').innerText = scope.ngModel.config.title;
                    
                    let valueElement = elem[0].querySelector('.value');
                    let statusElement = elem[0].querySelector('.status');
                    
                    elem[0].addEventListener("click",function(){ scope.sendCmd(itemName, scope.itemState(itemName) == 'ON' ? 'OFF' : 'ON'); });
                    
                    scope.$$postDigest(function()
                    {
                        scope.addUpdateListener(function ( updatedItemName )
                        {
                            if( updatedItemName != null && updatedItemName != itemName ) 
                            {
                                return;
                            }

                            var value = scope.itemState( itemName );
                            
                            valueElement.innerText = value == 'ON' ? 'An' : 'Aus';
                            
                            MV.handleClassList( value == 'ON', "active", valueElement.classList );
                            MV.handleClassList( value == 'ON', "active", statusElement.classList );
                        });
                    });
                }
            }
        }
    })();

    (function() {
        'use strict';

        app.directive("mvSlider", mvSliderLinker);
        
        mvSliderLinker.$inject = ['$document','$timeout'];
        function mvSliderLinker($document,$timeout) 
        {
            function getEventAttr(event, attr) 
            {
                return event.originalEvent === undefined ? event[attr] : event.originalEvent[attr];
            }
            
            function getEventXY(event, targetTouchId, attr) 
            {
                var clientXY = true ? 'clientY' : 'clientX'

                if (event[clientXY] !== undefined) return event[clientXY];

                var touches = getEventAttr(event, attr)

                if (targetTouchId !== undefined)
                {
                    for (var i = 0; i < touches.length; i++) 
                    {
                        if (touches[i].identifier === targetTouchId) 
                        {
                            return touches[i][clientXY]
                        }
                    }
                }

                return touches[0][clientXY]
            }

            return {
                restrict: "A",
                link: function (scope, elem, attrs) 
                {
                    let itemName = scope.ngModel.config.item;
                    let eventNames = {};
                    let touchId = false;
                    
                    let startPos = 0;
                    let maxOffset = 0;
                    let startOffset = 0;
                    
                    elem[0].querySelector('.widgetTitle').innerText = scope.ngModel.config.title;

                    let barElement = elem[0].querySelector('.bar');
                    let selectionElement = elem[0].querySelector('.selection');
                    let pointerElement = selectionElement.querySelector('.pointer');
                    let valueElement = selectionElement.querySelector('.value');

                    if( 'ontouchstart' in document.documentElement )
                    {
                        eventNames.clickEvent = 'touchend'
                        eventNames.startEvent = 'touchstart'
                        eventNames.moveEvent = 'touchmove'
                        eventNames.stopEvent = 'touchend'
                    }
                    else
                    {
                        eventNames.clickEvent = 'click'
                        eventNames.startEvent = 'mousedown'
                        eventNames.moveEvent = 'mousemove'
                        eventNames.stopEvent = 'mouseup'
                    }
                    
                    function onClick(event)
                    {
                        if( event.target != pointerElement )
                        {
                            let halfSelectionHeight = (selectionElement.clientHeight / 2);
                            
                            let adjustedClickOffset = event.layerY;
                            if( adjustedClickOffset == undefined )
                            {
                                let currentPos = getEventXY(event,touchId,'changedTouches');
                                adjustedClickOffset = currentPos - barElement.getBoundingClientRect().y; 
                            }

                            if( adjustedClickOffset < halfSelectionHeight ) adjustedClickOffset = halfSelectionHeight;
                            else if( adjustedClickOffset > barElement.clientHeight - halfSelectionHeight ) adjustedClickOffset = barElement.clientHeight - halfSelectionHeight;
                            
                            let currentOffset = barElement.clientHeight - (adjustedClickOffset + halfSelectionHeight) ;
                            
                            let currentValue = currentOffset * 100 / ( barElement.clientHeight - selectionElement.clientHeight );
                            
                            refreshValue(currentValue, currentOffset );
                            
                            scope.sendCmd(itemName,valueElement.innerText);
                        }
                    }
                    
                    function onStart(event)
                    {
                        event.stopPropagation();
                        event.preventDefault();

                        $document.on(eventNames.moveEvent,onMove);
                        $document.on(eventNames.stopEvent,onStop);
                        
                        var changedTouches = getEventAttr(event, 'changedTouches');
                        if (changedTouches) touchId = changedTouches[0].identifier;
    
                        startPos = getEventXY(event,touchId,'touches');

                        maxOffset = barElement.clientHeight - selectionElement.clientHeight;
                        startOffset = maxOffset - selectionElement.offsetTop;
                    }
                    
                    function onMove( event )
                    {
                        event.stopPropagation();
                        
                        let currentPos = getEventXY(event,touchId,'touches');
                        
                        let diff = startPos - currentPos;
                        let currentOffset = startOffset + diff;
                        if( currentOffset < 0 ) currentOffset = 0;
                        else if( currentOffset > maxOffset ) currentOffset = maxOffset;
    
                        let currentValue = ( currentOffset * 100 / maxOffset );
                        
                        refreshValue(currentValue,currentOffset);
                    }

                    function onStop( event )
                    {
                        event.stopPropagation();
                        event.preventDefault();
                        
                        scope.sendCmd(itemName,valueElement.innerText);

                        $document.off(eventNames.moveEvent,onMove);
                        $document.off(eventNames.stopEvent,onStop);
                    }

                    function refreshValue( value, offset )
                    {
                        if( value == 'ON' ) value = 100;
                        else if( value == 'OFF' ) value = 0;
    
                        /*var parts = item.state.split(',');
                        var value;
                        if (parts.length == 3) {
                            // slider received HSB value, use the 3rd (brightness)
                            value = parseFloat(parts[2]);
                        } else if (parts.length == 1) {
                            value = parseFloat(parts[0]);
                        } else {
                            return undefined;
                        }*/
                
                        value = Math.round(value);
                        if( value > 100 ) value = 100;
    
                        valueElement.innerText = value;
                        
                        offset = "calc(" + value + "% - " + ( ( value * 32 / 100 ) + 5 ) + "px)";
                        
                        /*if( offset == undefined )
                        {
                            offset = "calc(" + value + "% - " + ( value * 32 / 100 ) + "px)";
                        }
                        else
                        {
                            offset = offset + "px";
                        }*/
                        
                        selectionElement.style="bottom:" + offset;
                    }
                    
                    pointerElement.addEventListener(eventNames.startEvent,onStart);
                    barElement.addEventListener(eventNames.clickEvent,onClick);
                    
                    scope.$$postDigest(function()
                    {
                        scope.addUpdateListener(function ( updatedItemName )
                        {
                            if( updatedItemName != null && updatedItemName != itemName ) 
                            {
                                return;
                            }

                            refreshValue( scope.itemState( itemName ) );
                        });
                    });
                    
                    scope.$on('$destroy', function()
                    {
                        //pointerElement.removeEventListener(eventNames.startEvent,onStart);
                        //barElement.removeEventListener(eventNames.clickEvent,onClick);
                        $document.off(eventNames.moveEvent,onMove);
                        $document.off(eventNames.stopEvent,onStop);
                    });
                }
            };
        }
    })();

    (function() {
        'use strict';

        app.directive("mvRollershutter", mvRollerShutterLinker);
        
        function mvRollerShutterLinker() {
            return {
                restrict: "A",
                link: function (scope, elem, attrs) 
                {
                    let itemName = scope.ngModel.config.item;
                    let watchedItemNames = [];

                    elem[0].querySelector(".widgetTitle").innerText = scope.ngModel.config.title;
                    
                    function refreshValue()
                    {
                        if( watchedItemNames.length == 0 )
                        {
                            let item = scope.getItem( itemName );
                            watchedItemNames.push( item.name );
                            
                            let items = scope.itemsInGroup( itemName );
                            for( var i = 0; i < items.length; i++ )
                            {
                                watchedItemNames.push( items[i].name );
                            }
                        }
                        
                        let isAllUp = true;
                        let isAllDown = true;
                        
                        for( var i in watchedItemNames )
                        {
                            let value = scope.itemState( watchedItemNames[ i ] );
                            switch( value )
                            {
                                case '0':
                                case 'UP':
                                    isAllDown = false;
                                    break;
                                case '100':
                                case 'DOWN':
                                    isAllUp = false;
                                    break;
                                default:
                                    isAllUp = false;
                                    isAllDown = false;
                                    break;                            
                            }
                        }
                        
                        MV.handleClassList( isAllUp, "upActive", elem[0].classList );
                        
                        MV.handleClassList( isAllDown, "downActive", elem[0].classList );
                    }
                    
                    scope.$$postDigest(function()
                    {
                        scope.addUpdateListener(function ( updatedItemName )
                        {
                            if( updatedItemName !=null && watchedItemNames != null && watchedItemNames.indexOf( updatedItemName ) == -1 )
                            {
                                return;
                            }
                            
                            refreshValue();
                        });
                    });
                }
            };
        }
    })();

    (function() {
        'use strict';

        app.directive("mvOutdoorLight", mvOutdoorLightLinker);
        
        function mvOutdoorLightLinker() {
            return {
                restrict: "A",
                link: function (scope, elem, attrs) 
                {
                    let manualItemName = scope.ngModel.config.manualItem;
                    let autoItemName = scope.ngModel.config.autoItem;

                    elem[0].querySelector('.widgetTitle').innerText = scope.ngModel.config.title;
                    
                    let manualValueElement = elem[0].querySelector('button.manual span');
                    let autoValueElement = elem[0].querySelector('button.auto span');

                    let columnElement = elem[0];
                    
                    let manualStatusElements = elem[0].querySelectorAll('.manual');
                    function handleManual(){ scope.sendCmd(manualItemName, scope.itemState(manualItemName) == 'ON' ? 'OFF' : 'ON'); }
                    for( var statusElement of manualStatusElements ) statusElement.addEventListener("click",handleManual);

                    function handleAuto(){ scope.sendCmd(autoItemName, scope.itemState(autoItemName) == 'ON' ? 'OFF' : 'ON'); }
                    let autoStatusElements = elem[0].querySelectorAll('.auto');
                    for( var statusElement of autoStatusElements ) statusElement.addEventListener("click",handleAuto);
                    
                    scope.$$postDigest(function()
                    {
                        scope.addUpdateListener(function ( updatedItemName )
                        {
                            if( updatedItemName != null && updatedItemName != manualItemName && updatedItemName != autoItemName ) 
                            {
                                return;
                            }

                            var manualValue = scope.itemState( manualItemName );
                            //manualValueElement.innerText = manualValue == 'ON' ? 'An' : 'Aus';
                            
                            var autoValue = scope.itemState( autoItemName );
                            //autoValueElement.innerText = autoValue == 'ON' ? 'An' : 'Aus';
                            
                            MV.handleClassList( manualValue == 'ON', "manualActive", columnElement.classList );
                            MV.handleClassList( autoValue == 'ON', "autoActive", columnElement.classList );
                        });
                    });
                }
            }
        }
    })();

    (function() {
        'use strict';

        app.directive("mvOutdoorLightAutomatic", mvOutdoorLightLinker);
        
        function mvOutdoorLightLinker() {
            return {
                restrict: "A",
                link: function (scope, elem, attrs) 
                {
                    let mainItemName = scope.ngModel.config.mainItem;
                    let itemGroupName = scope.ngModel.config.itemGroup;
                    let sceneItemName = scope.ngModel.config.sceneItem;

                    let columnElement = elem[0];
                    
                    let manualStatusElements = elem[0].querySelectorAll('.manual');
                    function handleManual(){ scope.sendCmd(mainItemName, scope.itemState( mainItemName ) == 'ON' ? 'OFF' : 'ON'); }
                    for( var statusElement of manualStatusElements ) statusElement.addEventListener("click",handleManual);

                    let sceneElement = elem[0].querySelector('.scene');
                    sceneElement.addEventListener("click",function(){ scope.sendCmd(sceneItemName, 'ON'); } );

                    function handleAuto(){ scope.sendCmd(mainItemName, scope.itemState( itemGroupName ) != 'Inaktiv' ? 'OFF' : 'ON'); }
                    let autoStatusElements = elem[0].querySelectorAll('.auto');
                    for( var statusElement of autoStatusElements ) statusElement.addEventListener("click",handleAuto);
                    
                    scope.$$postDigest(function()
                    {
                        scope.addUpdateListener(function ( updatedItemName )
                        {
                            if( updatedItemName != null && updatedItemName != mainItemName && updatedItemName != itemGroupName && updatedItemName != sceneItemName ) 
                            {
                                return;
                            }
                            
                            var mainValue = scope.itemState( mainItemName );
                            var groupValue = scope.itemState( itemGroupName );
                            
                            MV.handleClassList( mainValue == 'ON', "manualActive", columnElement.classList );
                            MV.handleClassList( groupValue == 'Inaktiv', "autoActive", columnElement.classList );
                        });
                    });
                }
            }
        }
    })();

    (function() {
        'use strict';

        app.directive("mvTemperature", mvTemperatureLinker);
        
        function mvTemperatureLinker() {
            return {
                restrict: "A",
                link: function (scope, elem, attrs) 
                {
                    let itemName = scope.ngModel.config.item;
                    let itemSubName = scope.ngModel.config.itemSub;

                    elem[0].querySelector('.widgetTitle').innerText = scope.ngModel.config.title;
                    
                    let mainValueElement = elem[0].querySelector('.top .value .main');
                    let subValueElement = elem[0].querySelector('.bottom .value span');

                    scope.$$postDigest(function()
                    {
                        scope.addUpdateListener(function ( updatedItemName )
                        {
                            if( updatedItemName != null && updatedItemName != itemName && updatedItemName != itemSubName ) 
                            {
                                return;
                            }

                            var mainValue = scope.itemState( itemName );
                            mainValueElement.innerText = parseFloat(mainValue).toFixed(1);
                            
                            var subValue = scope.itemState( itemSubName );
                            subValueElement.innerText = parseFloat(subValue).toFixed(1);
                        });
                    });
                }
            }
        }
    })();

    (function() {
        'use strict';

        app.directive("dashboardButton", dashboardButtonLinker);
        
        dashboardButtonLinker.$inject = ['$location'];
        function dashboardButtonLinker($location) {
            return {
                restrict: "A",
                link: function (scope, elem, attrs) {                
                    var dashboard = "";
                    if( attrs.dashboard )
                    {
                        dashboard = attrs.dashboard;
                    }
                    else
                    {
                        elem[0].childNodes[0].innerText = scope.ngModel.config.title;
                        
                        if( scope.ngModel.config.type )
                        {
                            //console.log("add: " + scope.ngModel.type);
                            elem[0].parentNode.classList.add(scope.ngModel.config.type);
                        }
                        
                        dashboard = scope.ngModel.config.dashboard;
                    }
                    elem[0].addEventListener("click", function () {
                        scope.$evalAsync(function(){
                            //console.log("onclick");
                            $location.url("/view/" + dashboard + ( attrs.dashboardParameter ? "?" + attrs.dashboardParameter : "" ));
                        });
                    });
                }
            };
        }
    })();







    /*********************************
    *                               *
    * CUSTOM NON REUSABLE WIDGETS   *
    *                               *
    *********************************/

    (function() {
        'use strict';
        
        app.directive("mvClock", mvClockLinker);
        
        mvClockLinker.$inject = ['$timeout'];
        function mvClockLinker($timeout) {
            return {
                restrict: 'AE',
                template: '<div></div><div></div>',
                link: function(scope, element, attrs) {
                    
                    let timeElement = element[0].childNodes[0];
                    let dateElement = element[0].childNodes[1];
                    let timer = null;
                    
                    const monthNames = ["January", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"];
                    const weekdayNames = ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"];

                    function triggerHandler()
                    {
                        let diff = 0;
                
                        var d = new Date(), 
                            h = new Date(d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes() + 1, 0, 0);
                        diff = h - d;
                        
                        let hours = ( d.getHours() < 10 ? "0":"" ) + d.getHours();
                        let minutes = ( d.getMinutes() < 10 ? "0":"" ) + d.getMinutes();
                        
                        timeElement.innerText = hours + ":" + minutes;
                        dateElement.innerText = weekdayNames[d.getDay()] + ", der " + d.getDate() + ". " + monthNames[d.getMonth()] + " " + d.getFullYear();

                        timer = $timeout(triggerHandler,diff,false);
                    }
                    
                    triggerHandler();
                    
                    scope.$on('$destroy', function (event) 
                    {
                        $timeout.cancel(timer);
                    });
                }
            }
        }
    })();

    (function() {
        'use strict';

        app.directive('mvWidgetEmbedd', mvEmbedd);
            
        mvEmbedd.$inject = ['$timeout','mvService'];
        function mvEmbedd($timeout,mvService) {
            return {
                restrict: 'AE',
                template: '<div></div>',
                link: function (scope, element, attrs) {
                    //scope.vm.url = attrs.url;
                    //scope.vm.interval = attrs.interval;
                    
                    function initLoader()
                    {
                        var timeoutPromise;
                        
                        let triggerHandler = function( scope )
                        {
                            loadContent( scope, element, attrs );
                            
                            let timeout = 0;
                            if( attrs.embeddRefreshInterval == 3600 )
                            {
                                var d = new Date(), h = new Date(d.getFullYear(), d.getMonth(), d.getDate(), d.getHours() + 1, 0, 0, 0);
                                let diff = h - d;
                                // 300 sec => 5min after
                                timeout = diff + 300000;
                            }
                            else
                            {
                                timeout = attrs.embeddRefreshInterval * 1000   
                            }
                            
                            timeoutPromise = $timeout(function (){ triggerHandler( scope ); }, timeout, 0, false);
                        }
                        
                        triggerHandler( scope );
                        
                        mvService.addRefreshListener(loadContent);

                        scope.$on('$destroy', function (event) 
                        {
                            $timeout.cancel(timeoutPromise);
                            mvService.removeRefreshListener(loadContent);
                        });
                    }

                    function loadContent()
                    {
                        //var _url = "//" + authType + domain + attrs.embeddUrl;
                        var _url = attrs.embeddUrl;
                        
                        let contentElement = element[0].childNodes[0];
                        
                        _url += ( _url.indexOf("?") == -1 ? "?" : "&" ) + 'rand=' + Math.random();
                        
                        var xhr = new XMLHttpRequest();
                        xhr.withCredentials = true;
                        xhr.open("GET", _url);
                        xhr.onload = function() 
                        {
                            sessionStorage.setItem('mvWidgetEmbedd.embeddUrl_'+attrs.embeddUrl, this.response);

                            contentElement.innerHTML = this.response;

                            let eventListenerElements = contentElement.querySelectorAll('[mv-url]');
                            
                            for( var i = 0; i < eventListenerElements.length; i++ )
                            {
                                let eventListenerElement = eventListenerElements[i];
                                
                                let clickUrl = eventListenerElement.getAttribute('mv-url');

                                eventListenerElement.addEventListener("click",function()
                                {
                                    attrs.embeddUrl = clickUrl;
                                    loadContent(scope,element, attrs);
                                });
                            }
                        }
                        xhr.send();
                    }

                    var timeout = 0;
                    // force last cached img
                    if( sessionStorage.getItem( 'mvWidgetEmbedd.embeddUrl_'+attrs.embeddUrl) )
                    {
                        //console.log("use cache 2");
                        element[0].childNodes[0].innerHTML = sessionStorage.getItem( 'mvWidgetEmbedd.embeddUrl_'+attrs.embeddUrl);
                        timeout = 700;
                    }

                    scope.$$postDigest(function()
                    {
                        //console.log("start embed");
                        $timeout(function(){ initLoader( scope, element, attrs ); },timeout,false);
                        //console.log("finish embed");
                    });
                }
            };
        }
    })();

    (function() {
        'use strict';

        app.directive('mvWidgetImagePopup', mvImagePopup);
            
        mvImagePopup.$inject = ['$timeout'];
        function mvImagePopup($timeout) 
        {
            return {
                restrict: 'AE',
                template: '<div><img></div>',
                link: function(scope, element, attrs) {
                    var inlineUrl = "//" + authType + domain + "/" + scope.ngModel.config.imageUrl;
                    var popupUrl = "//" + authType + domain + "/" + scope.ngModel.config.streamUrl;
                    var inlineRefreshInterval = scope.ngModel.config.imageRefresh;
                    var imageWidth = 0;
                    var imageHeight = 0;
                    var timeoutRef = null;
                    
                    function setInlineUrl( element )
                    {
                        let _url = inlineUrl;
                        
                        _url += ( _url.indexOf("?") == -1 ? "?" : "&" ) + 'rand=' + Math.random();
                    
                        _url = _url.replace("{width}",imageWidth);//element.parent()[0].clientWidth);
                        _url = _url.replace("{height}",imageHeight);//:,element.parent()[0].clientHeight);
                        _url = _url.replace("{age}",inlineRefreshInterval * 1000);
                        
                        var img = new Image();
                        img.onload = function()
                        {
                            //console.log("set real");
                            element[0].firstChild.firstChild.src = _url;

                            sessionStorage.setItem('mvWidgetImagePopup.inlineUrl_'+inlineUrl, _url);
                        }
                        img.src = _url;
                    }
                    
                    function togglePopup( element, forceInline )
                    {
                        if( forceInline || element[0].firstChild.classList.contains("popup") )
                        {
                            //console.log("mvWidgetImagePopup: start inline refresh " + inlineRefreshInterval );

                            element[0].firstChild.classList.remove("popup");
                            
                            function handleTrigger()
                            {
                                //console.log("mvWidgetImagePopup: call inline refresh");
                                setInlineUrl( element );

                                timeoutRef = $timeout( handleTrigger, inlineRefreshInterval * 1000, 0, false);
                            }
                            
                            handleTrigger();
                            
                            scope.$on('$destroy', function (event) 
                            {
                                //console.log("mvWidgetImagePopup: cancel inline refresh");
                                $timeout.cancel(timeoutRef);
                            });
                        }
                        else
                        {
                            //console.log("mvWidgetImagePopup: stop inline refresh");

                            element[0].firstChild.classList.add("popup");
                            element[0].firstChild.firstChild.src = popupUrl;
                            
                            $timeout.cancel(timeoutRef);
                        }
                    }

                    function initLoader( $timeout, scope, element )
                    {
                        //console.log( element[0].clientWidth);
                        if( element[0].clientWidth > 0 )
                        {
                            imageWidth = element[0].clientWidth;
                            imageHeight = element[0].clientHeight;
                            togglePopup( element, true );
                            
                            element[0].addEventListener("click",function(){ togglePopup(element,false);});
                        }
                        else
                        {
                            $timeout(function() { initLoader( $timeout, scope,element); },100,false);
                        }
                    }

                    var timeout = 0;
                    // force last cached img
                    if( sessionStorage.getItem( 'mvWidgetImagePopup.inlineUrl_'+inlineUrl) )
                    {
                        //console.log("use cache");
                        element[0].firstChild.firstChild.src = sessionStorage.getItem( 'mvWidgetImagePopup.inlineUrl_'+inlineUrl);
                        timeout = 1000;
                    }
                    
                    scope.$$postDigest(function()
                    {
                        $timeout(function(){ initLoader( $timeout, scope, element ) }, timeout, false );
                    });
                }
            };
        }	
    })();

    (function() {
        'use strict';
        
        app.directive("paperUi", paperUILinker);

        function paperUILinker() {
            return {
                restrict: "A",
                link: function (scope, elem, attrs) 
                {
                    var pos = document.location.hash.indexOf("?");
                    if( pos != -1 )
                    {
                        elem[0].src = elem[0].src + "?" + document.location.hash.substr(pos+1);
                    }
                    
                    elem[0].style="visibility:hidden";
                    elem[0].addEventListener("load", function()
                    {
                        let element = elem[0].contentWindow.document.querySelector('main');
                        element.style="background: transparent !important;";

                        element = elem[0].contentWindow.document.querySelector('body');
                        element.style="background: transparent !important;";

                        elem[0].style="";
                        
                        var css = '.mdl-form {';
                        css = css + "background-color: black !important;";
                        css = css + "color: white !important;";
                        css = css + "}";
                        css = css + "body { font-family: Roboto; }";
                        css = css + ".mdl-form__row {border-bottom: 1px solid rgba(38,191,117,.50);}";
                        css = css + ".mdl-form__label, .mdl-form__text, .mdl-form__value--text-link { font-size:17px; }";
                        css = css + ".mdl-layout__header { background-color: black !important; border-bottom: 1px solid rgba(38,191,117,.50);}";
                        css = css + ".mdl-slider__background-upper { background-color: white !important;}";
                        css = css + ".mdl-form input[type=range].is-lowest-value::-webkit-slider-thumb { background-color: white !important;}";
                        css = css + ".mdl-form input[type=range].is-lowest-value::-moz-range-thumb { background-color: white !important;}";
                        //css = css + ".mdl-layout__header { background-color: rgba(38,191,117,.1) !important; border-bottom: 1px solid rgba(38,191,117,.50);}";
                        
                        var head = elem[0].contentWindow.document.getElementsByTagName('head')[0];
                        var style = elem[0].contentWindow.document.createElement('style');
                        style.appendChild(document.createTextNode(css));
                        head.appendChild(style);
                    });
                }
            };
        }
    })();

    (function() {
        'use strict';
        
        app.directive("mvDetailInfoStatus", detailInfoStatusLinker);

        function detailInfoStatusLinker() {
            return {
                restrict: "A",
                link: function (scope, elem, attrs) 
                {
                    let stateItemName = "Watering_Program_State";
                    let circuitItemName = "Watering_Circuits";
                    
                    function getSVG(icon_name)
                    {
                        let msg = "<svg style=\"width:16px;height:16px;stroke:var(--sub-icon-color);filter:brightness(150%);\" version=\"1.1\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" viewBox=\"0 0 64 64\">";
                        msg += "<use xmlns:xlink=\"http://www.w3.org/1999/xlink\" xlink:href=\"/static/theme/svg/icons.svg#" + icon_name + "\"></use>";
                        msg += "</svg>";
                        return msg;
                    }
                    
                    function updateValue()
                    {
                        let msg_r = [];
                            
                        if( scope.itemState(circuitItemName) == 'ON' )
                        {
                            let programState = scope.itemState(stateItemName);
                            
                            if( programState != "läuft nicht" )
                            {
                                msg_r.push( "Bewässerung: " + getSVG('self_rain_grayscaled') + " <span class=\"value\">" + programState + "</span>" );
                            }
                        }
                        else
                        {
                            //msg_r.push( "Bewässerung: " + getSVG('openhab_rain_colored') + " <span class=\"value\">Garten links gleich fertig</span>" );
                        }

                        elem[0].innerHTML = "<div>" + msg_r.join("</div><div>") + "</div>";
                    }
                    
                    scope.$$postDigest(function()
                    {
                        // register for item usage
                        //scope.getItem(stateItemName);
                        //scope.getItem(circuitItemName)

                        scope.addUpdateListener(function( updatedItemName )
                        {
                            //console.log("Watering_Circuits initialized");
                            if( updatedItemName != null && updatedItemName != stateItemName && updatedItemName != circuitItemName )
                            {
                                return;
                            }
                            
                            updateValue();
                                    
                            //elem[0].querySelector(".value").innerHTML = "Bewässerung: Garten links gleich fertig";
                        });
                        
                        // getItem triggers a watcher registration process
                        //if( scope.getItem(circuitItemName) != null )
                        //{
                            //updateValue();
                        //}
                    });
                }
            };
        }
    })();
};

mvInitializer();


