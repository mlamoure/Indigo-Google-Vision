Indigo (http://www.indigodomo.com) plugin for Google Vision, allowing home automation integration with the Google Vision API results.

# Requirements #
A Google Cloud Account with access to the Vision API
In order to make the plugin usefeul to you, you'll need some kind of web-enabled camera that is integrated into your Indigo setup

# Features #

Events:
* Face Detection - Looks for faces in the image. You can configure the level of certainty that Google returns back to the plugin. Also supported is a flag to look for "no faces detected". Google's API's also support things like the likelihood that the face is showing joy, anger, sorrow, etc. I have not implemented those.

* Label (Object) Detection - Looks for objects in photos. Easiest way to understand Google's dictionary is test with your own images and see what results typically come back.  Typical use cases is to detect the presence of a person, automobile, pet.

* OCR - I haven't tested this thoroughly, but the plugin can trigger an event if Google is able to OCR text in a image and you are looking for a particular substring.

Actions:
* Send Image - This Action sends an image to Google Vision API.  Images can be local to your Indigo Server or available via HTTP.  The web server needs to be accessible to Google's servers (not just the Indigo Server) for HTTP to work.  The location/URL can be set statically in the Action config, or via Indigo variable.

# Install #
1. Get a Google Cloud Account, and API key if you dont have one (cost of the Google Vision API is listed here: https://cloud.google.com/vision)
2. Enable the Google Vision API for your Account
3. Install and configure the plugin

# Configure #
1. Add your API key to the plugin via the configuration menu
2. Set up events using Plugins -> Google Vision -> Setup Events
3. Create actions to send an image to Google Vision
4. Create triggers to react to the events you created in step #1

Note: This plugin does not require to create any devices.
