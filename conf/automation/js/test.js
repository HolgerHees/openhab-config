//const runtime = require("@runtime");
const helper = require("helper");

helper.JSRule(class Test{
    abc = 1;

    triggers() {
        return [triggers.GenericCronTrigger("0 */5 * * * ?")];
//        return [triggers.GenericCronTrigger("*/5 * * * * ?")];
    }

    execute(event) {
        //this.logger.info("test");
        //const test = 1 / tst;
        //console.log(this.abc);
        //console.log("test");
    }
});

