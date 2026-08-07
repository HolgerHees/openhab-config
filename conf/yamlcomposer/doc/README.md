After my last project—porting my HABPanel dashboard to the standard WebUI—I decided to move on to the Basic UI this time.

The previously mentioned dashboard presented key data reasonably well, but it was far from sufficient on its own. To handle this, I had a very extensive sitemap that provided access to all 1,174 of my items. In the dashboard, I would either access this sitemap directly via the start URL to reach everything or jump straight to specific sections—like the heating or ventilation menus—using sub-URLs.

Having had a positive experience porting the dashboard, I decided to try the same approach with the sitemap.

The following advantages were decisive for me:
1. A WebUI-based solution can still be accessed via the Android app.
2. I can now customize minor details of the app UI design to my liking.
3. I no longer need to embed the sitemap as an iframe within a dashboard popup.
4. The layout is now consistent between the dashboard and the new app design.
5. It offers entirely new interaction possibilities.

Initially, I tried implementing this using "standard" widgets. Unfortunately, I didn't get very far because the widget API is quite limited. Since I was working with the YAML composer at the time, I opted for a hybrid approach; consequently, my solution makes extensive use of the YAML composer.

I also initially attempted to implement each of my screens as a separate "Page." However, I noticed a perceptible 0.5-second lag during navigation, so I switched to using a single central page for the app and another for the tablet dashboard. Within these pages, I simply switch between widgets.

For me, the implementation is 100% feature-complete—meaning:

- The layout behaves exactly like the app's; it is responsive and switches between one-column and two-column layouts. The following features have also been implemented:
- Dimmer with Hue color support
- Text input
- Roller shutter controls
- Selection (using both item options and custom mappings)
- Setpoints
- Choice buttons
- Toggle buttons
- Text boxes with the ability to navigate to sub-pages

Additionally, value colors and the visibility flag have been implemented.

For now, everything is implemented to the point where it can fully replace the old version and serve as the detail navigation in my tablet dashboard.

Anything beyond this can be added next.

P.S. The layout still needs some fine-tuning.
