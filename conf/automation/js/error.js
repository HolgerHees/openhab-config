const helper = require("helper");

const { itemRegistry } = require('@runtime');

helper.JSRule(class ErrorMessage{
    triggers() {
//        return [triggers.GenericCronTrigger("*/15 * * * * ?")];
        return [triggers.GenericCronTrigger("0 * * * * ?")];
    }

    check() {
        itemRegistry.getItem("eOther_Error").getAllMembers().forEach( item => {
            if( item.getState() != null && item.getState().length > 0) {
                console.log("STATE: " + item.getLabel() + " - " + item.getState());
            }
        });

        /*const members = items.getItem("eOther_Error").descendents;
        items.getItem("eOther_Error").members.forEach( item => {
            if( item.rawState != null && item.state.length > 0) {
                console.log("STATE: " + item.label + " - " + item.state);
            }
        });*/
    }

    execute(event) {
        //this.check()
    }
});
