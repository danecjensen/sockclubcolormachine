# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import webapp2
import os
import cgi
from google.appengine.ext.webapp import template
from google.appengine.ext import ndb
from google.appengine.api import images
from google.appengine.ext import vendor

vendor.add('lib')

import numpy as np
import PIL
from PIL import Image
import urllib2
import random
from io import BytesIO
import logging
import mimetypes
import json

import boto3


COLORS = ["#ece7d9", "#cdbfaa", "#000000", "#f4f3f3", "#f5bfca", "#1963ac", "#4f5457", "#f68d3f", "#9aa9ab", "#24aae1", "#db1280", "#d8cd4a", "#774679", "#288741", "#0d4166", "#92c9d5", "#9fc73c", "#6b232a",
          "#aa8e74", "#052a3f", "#2e3032", "#14b1be", "#ee502a", "#1e3e22", "#652257", "#d92026", "#b72327", "#129e7a", "#3f2c25", "#452971", "#f8bb15", "#00867b", "#6c9d40", "#29358d", "#f8e03a", "#5ca2d8", "#e34f94"]

awslambda = boto3.client('lambda', aws_access_key_id="AKIAJDDQRXPHFCLTR35A",
                         aws_secret_access_key="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", region_name='us-east-1')


def convert_color(c1, c2, data):
    # change color c1 to color c2
    (red, green, blue) = data[:, :, 0], data[:, :, 1], data[:, :, 2]
    mask = (red == c1[0]) & (green == c1[1]) & (blue == c1[2])
    data[:, :, :3][mask] = [c2[0], c2[1], c2[2]]
    return data


def hex_to_rgb(hex):
    hex = hex.lstrip('#')
    hlen = len(hex)
    return tuple(int(hex[i:i + int(hlen / 3)], 16) for i in range(0, hlen, int(hlen / 3)))


def chunks(l, n):
    for i in range(0, len(l) - n):
        yield l[i:i + n]


class Design(ndb.Model):
    filename = ndb.StringProperty()
    image = ndb.BlobProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)

    # def uri2view(self):  # enable get_serving_url
    #     # logging.info(str(images.get_serving_url(
    #     #     self.image.key(), secure_url=True)))
    #     # return
    #     # images.get_serving_url("aghkZXZ-Tm9uZXITCxIGRGVzaWduGICAgICA0LsJDA",
    #     # secure_url=True)
    #     # return str(images.get_serving_url(
    #     #     self.image.key(), secure_url=True))
    #     logging.info("/design_serve/" + str(self.id))
    #     # return "/design_serve/" + str(self.id)
    #     return "https://www.sockclub.com/images/squiggles.bmp"

    @classmethod
    def query_all(cls):
        return cls.query().order(-cls.created)

    @classmethod
    def query_20(cls):
        return cls.query().order(-cls.created).fetch(limit=20)

    @classmethod
    def query_20_run(cls):
        return cls.query().order(-cls.created).run(limit=20)

    @classmethod
    def get_all(cls):
        q = cls.Query()
        q.order('-created')
        return q.fetch(limit=20)


class Colorways(ndb.Model):
    design_url = ndb.StringProperty()
    sock_colorways = ndb.BlobProperty(repeated=True)


class Deck(ndb.Model):
    client_name = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)

    @property
    def designs(self):
        return Design.query(ancestor=self.key)


class MainPage(webapp2.RequestHandler):

    def get(self):
        designs = Design.query_20()
        home = os.path.join(os.path.dirname(__file__),
                            'templates', "index.html")
        page = template.render(
            home, {'show_colorways': False, 'designs': designs})
        self.response.out.write(page)

    def post(self):
        designs = Design.query_20()
        design = cgi.escape(self.request.get('design'))
        file = BytesIO(
            urllib2.urlopen(design).read())
        im = Image.open(file)
        im = im.convert('RGB')
        init_colors = im.getcolors()
        orig_sock = np.array(im)
        new_sock = orig_sock.copy()
        colors_array = []
        socks_array = []

        for i in range(37):
            for c in init_colors:
                # print colors_array
                rindex = random.randint(0, 36)
                if rindex not in colors_array:
                    colors_array.append(rindex)
                    if not (c == (255, 255, 255)):
                        new_sock = convert_color(
                            c[1], hex_to_rgb(COLORS[rindex]), new_sock)
            new_im = Image.fromarray(new_sock)
            bitmap = BytesIO()
            new_im.save(bitmap, "PNG")
            image_bytes = bitmap.getvalue()
            socks_array.append(image_bytes)
            colors_array = []
            new_sock = orig_sock.copy()

        colorways = Colorways(design_url=design, sock_colorways=socks_array)
        colorways_key = colorways.put()

        home = os.path.join(os.path.dirname(__file__),
                            'templates', "index.html")
        page = template.render(
            home, {'colorways_id': colorways_key.id(), 'show_colorways': True, 'designs': designs})
        self.response.out.write(page)


class PDFTest(webapp2.RequestHandler):

    def get(self):
        images = []
        file = BytesIO(urllib2.urlopen(
            "https://account-sockclub-com.s3.amazonaws.com/deck_creation/5694660253057024_deck_page1.jpg").read())
        im = Image.open(file)
        im = im.convert('RGB')
        im = im.resize((595, 842), Image.ANTIALIAS)

        file = BytesIO(urllib2.urlopen(
            "https://account-sockclub-com.s3.amazonaws.com/deck_creation/5694660253057024_deck_page2.jpg").read())
        im2 = Image.open(file)
        im2 = im2.convert('RGB')
        im2 = im2.resize((595, 842), Image.ANTIALIAS)

        images.append(im2)

        logging.info(PIL.__version__)

        pdf = BytesIO()
        im.save(pdf, "PDF", quality=100, save_all=True, append_images=images)
        # logging.info(pdf.getvalue())
        self.response.headers['Content-Type'] = "application/pdf"
        self.response.out.write(pdf.getvalue())


class ArgyleBitmapBuilderPage(webapp2.RequestHandler):

    def get(self):
        # cgi.escape(self.request.get('username'))
        # template_id = cgi.escape(self.request.get('template_id'))

        bb = os.path.join(os.path.dirname(__file__),
                          'templates', "bitmap_builder.html")
        page = template.render(bb, {})
        self.response.out.write(page)


class KnitPage(webapp2.RequestHandler):

    def get(self):
        # cgi.escape(self.request.get('username'))
        # template_id = cgi.escape(self.request.get('template_id'))
        designs = Design.query_20()
        wik = os.path.join(os.path.dirname(__file__),
                           'templates', "will_it_knit.html")
        page = template.render(wik, {'designs': designs})
        self.response.out.write(page)

    def post(self):
        designs = Design.query_20()
        design = cgi.escape(self.request.get('design'))
        file = BytesIO(
            urllib2.urlopen(design).read())
        im = Image.open(file)
        im = im.convert('RGB')
        pixels = list(im.getdata())
        width, height = im.size
        pixels = [pixels[i * width:(i + 1) * width] for i in xrange(height)]
        errors = ""
        row = 1
        last_row_printed = 0
        wik_word = "YES"
        wik_bool = True
        for i in pixels:
            # print i
            # print len(set(i))
            if (len(set(i)) > 6):
                errors = errors + "Too many colors on row: " + str(row) + "\n"

            for c in chunks(i, 30):
                if (len(set(c)) > 4):
                    if last_row_printed != row:
                        errors = errors + "More than 5 colors in 30 stitches on row: " + \
                            str(row) + "\n"
                        last_row_printed = row

            row = row + 1

        if errors != "":
            wik_word = "NO"
            wik_bool = False

        wik = os.path.join(os.path.dirname(__file__),
                           'templates', "will_it_knit.html")
        page = template.render(
            wik, {'show_wik': True, 'wik_word': wik_word, 'errors': errors, 'designs': designs})
        self.response.out.write(page)


class DeckCreationPage(webapp2.RequestHandler):

    def get(self):
        # cgi.escape(self.request.get('username'))
        # template_id = cgi.escape(self.request.get('template_id'))
        designs = Design.query_20()
        dc = os.path.join(os.path.dirname(__file__),
                          'templates', "deck_creation.html")
        page = template.render(dc, {'designs': designs, 'show_results': False})
        self.response.out.write(page)

    def post(self):
        designs = Design.query_20()
        design = cgi.escape(self.request.get('design'))
        data = {
            'bmp': design, 'filename': "blah", "topColor": "cyan", "heelColor": "cyan", "toeColor": "cyan"}
        logging.info(data)
        response = awslambda.invoke(
            FunctionName='arn:aws:lambda:us-east-1:981532365545:function:create_deck_images', InvocationType='RequestResponse', Payload=json.dumps(data))

        result = json.loads(response.get('Payload').read())

        dc = os.path.join(os.path.dirname(__file__),
                          'templates', "deck_creation.html")
        page = template.render(
            dc, {'designs': designs, 'fsb': result['body']['fsb'], 'page1': result['body']['page1'], 'page2': result['body']['page2'], 'show_results': True})
        self.response.out.write(page)


class FSBImagePage(webapp2.RequestHandler):

    def get(self):
        # cgi.escape(self.request.get('username'))
        # template_id = cgi.escape(self.request.get('template_id'))
        designs = Design.query_20()
        dc = os.path.join(os.path.dirname(__file__),
                          'templates', "fsb_image.html")
        page = template.render(dc, {'designs': designs, 'show_results': False})
        self.response.out.write(page)

    def post(self):
        designs = Design.query_20()
        design = cgi.escape(self.request.get('design'))
        data = {
            'bmp': design, 'filename': "blah"}
        logging.info(data)
        response = awslambda.invoke(
            FunctionName='arn:aws:lambda:us-east-1:981532365545:function:create_fsb_image', InvocationType='RequestResponse', Payload=json.dumps(data))

        result = json.loads(response.get('Payload').read())

        dc = os.path.join(os.path.dirname(__file__),
                          'templates', "fsb_image.html")
        page = template.render(
            dc, {'designs': designs, 'fsb': result['body']['fsb'], 'show_results': True})
        self.response.out.write(page)


class LambdaPage(webapp2.RequestHandler):

    def get(self):
        data = {
            'bmp': "http://sockclubcolormachine.appspot.com/bmp_serve/5631568827645952", 'filename': "blah", "topColor": "cyan", "heelColor": "cyan", "toeColor": "cyan"}
        response = awslambda.invoke(
            FunctionName='arn:aws:lambda:us-east-1:981532365545:function:create_deck_images', InvocationType='RequestResponse', Payload=json.dumps(data))
        pdf_images = []
        result = json.loads(response.get('Payload').read())
        pdf_images.append(result['body']['page1'])
        pdf_images.append(result['body']['page2'])

        lp = os.path.join(os.path.dirname(__file__),
                          'templates', "lambda_page.html")
        page = template.render(
            lp, {'pdf_images': pdf_images, 'result': result})
        self.response.out.write(page)


class FileUpload(webapp2.RequestHandler):

    def post(self):
        file_upload = self.request.POST.get("file", None)
        filename = file_upload.filename
        design = Design(filename=filename,
                        image=file_upload.file.read())
        design.put()

        self.redirect('/')


class ImgServe(webapp2.RequestHandler):

    def get(self, colorways_id, sock_id):
        logging.info('This is the sock id: ' + sock_id)
        colorways = Colorways.get_by_id(int(colorways_id))
        self.response.headers['Content-Type'] = "image/png"
        self.response.write(colorways.sock_colorways[int(sock_id)])


class BmpServe(webapp2.RequestHandler):

    def get(self, resource):

        # design = ndb.Key('Design', resource).get()
        design = Design.get_by_id(int(resource))
        # design = Design.get(resource)
        self.response.headers['Content-Type'] = "image/bmp"
        self.response.write(design.image)


class BmpServeKey(webapp2.RequestHandler):

    def get(self, resource):

        design = ndb.Key(urlsafe=resource).get()
        # design = Design.get_by_id(int(resource))
        # design = dkey.get()
        self.response.headers['Content-Type'] = "image/bmp"
        self.response.write(design.image)


class BmpServeDeck(webapp2.RequestHandler):

    def get(self, deck_id, design_id):
        design = ndb.Key(Deck, deck_id, Design, design_id).get()
        logging.info(ndb.Key(Deck, deck_id, Design, design_id).urlsafe())
        logging.info(ndb.Key(Deck, deck_id, Design, design_id).id())
        logging.info(ndb.Key(Deck, deck_id, Design, design_id).string_id())
        self.response.headers['Content-Type'] = "image/bmp"
        self.response.write(design.image)


class DesignServe(webapp2.RequestHandler):

    def get(self, resource):

        # design = ndb.Key('Design', resource).get()
        design = Design.get_by_id(int(resource))
        # design = Design.get(resource)
        self.response.headers[
            b'Content-Type'] = mimetypes.guess_type(design.filename)[0]
        self.response.write(design.image)


class BitmapUploadPage(webapp2.RequestHandler):

    def get(self):
        # cgi.escape(self.request.get('username'))
        # template_id = cgi.escape(self.request.get('template_id'))

        bu = os.path.join(os.path.dirname(__file__),
                          'templates', "bitmap_upload.html")
        page = template.render(bu, {})
        self.response.out.write(page)

    def post(self):
        files = self.request.POST
        # logging.info("file_upload variable: " + str(files))
        deck = Deck(client_name="Sock Club Custom Socks")
        deck_key = deck.put()
        for file in files.values():
            # logging.info("file variable: " + str(file))
            # logging.info("file filename variable: " + str(file.filename))
            # logging.info("file file variable: " + str(file.file))
            # design = Design(filename=file.filename, image=file.file.read())
            Design(parent=deck_key, filename=file.filename,
                   image=file.file.read()).put()

        self.redirect('/deck/' + str(deck_key.id()))


class DeckPage(webapp2.RequestHandler):

    def get(self, resource):
        deck = Deck.get_by_id(int(resource))
        dc = os.path.join(os.path.dirname(__file__),
                          'templates', "deck_page.html")
        page = template.render(dc, {'deck': deck})
        self.response.out.write(page)


# class PdfPage(webapp2.RequestHandler):

#     def get(self, resource):
#         deck = Deck.get_by_id(int(resource))
#         dc = os.path.join(os.path.dirname(__file__),
#                           'templates', "pdf_page.html")
#         page = template.render(dc, {'deck': deck})
#         self.response.out.write(page)


class PdfDeckCreation(webapp2.RequestHandler):

    def post(self):
        deck_id = cgi.escape(self.request.get('deckId'))
        deck = Deck.get_by_id(int(deck_id))
        design_entities = deck.designs.fetch()

        pdf_images = []
        pdf_filename = str(deck_id) + ".pdf"

        for i in range(len(design_entities)):
            heelStr = "heelColor_" + str(i + 1)
            topStr = "topColor_" + str(i + 1)
            toeStr = "toeColor_" + str(i + 1)
            heel_form_data = cgi.escape(self.request.get(heelStr))
            toe_form_data = cgi.escape(self.request.get(toeStr))
            top_form_data = cgi.escape(self.request.get(topStr))
            logging.info(heel_form_data)
            logging.info(top_form_data)
            logging.info(toe_form_data)

            design_url = "http://sockclubcolormachine.appspot.com/bmp_serve_key/" + \
                str(design_entities[i].key.urlsafe())
            data = {'bmp': design_url, 'filename': design_entities[
                i].key.id(), 'topColor': top_form_data, 'toeColor': toe_form_data, 'heelColor': heel_form_data}
            logging.info(data)
            response = awslambda.invoke(FunctionName='arn:aws:lambda:us-east-1:981532365545:function:create_deck_images',
                                        InvocationType='RequestResponse', Payload=json.dumps(data))
            logging.critical("Response: \n")
            logging.critical(response)
            result = json.loads(response.get('Payload').read())
            logging.critical("Result: \n")
            logging.critical(result)
            if result.has_key("body"):
                pdf_images.append(result['body']['page1'])
                pdf_images.append(result['body']['page2'])

        response2 = awslambda.invoke(FunctionName='arn:aws:lambda:us-east-1:981532365545:function:images2pdf',
                                     InvocationType='RequestResponse', Payload=json.dumps({"images": pdf_images, "filename": pdf_filename}))

        pp = os.path.join(os.path.dirname(__file__),
                          'templates', "pdf_page.html")
        page = template.render(
            pp, {'pdf_images': pdf_images, "pdf_filename": pdf_filename})
        self.response.out.write(page)


class ZipDeckCreation(webapp2.RequestHandler):

    def post(self):
        deck_id = cgi.escape(self.request.get('deckId'))
        deck = Deck.get_by_id(int(deck_id))
        design_entities = deck.designs.fetch()

        pdf_images = []
        pdf_filename = str(deck_id) + ".zip"

        for i in range(len(design_entities)):
            heelStr = "heelColor_" + str(i + 1)
            topStr = "topColor_" + str(i + 1)
            toeStr = "toeColor_" + str(i + 1)
            heel_form_data = cgi.escape(self.request.get(heelStr))
            toe_form_data = cgi.escape(self.request.get(toeStr))
            top_form_data = cgi.escape(self.request.get(topStr))

            filename_num = 2 * (i + 1) - 1

            design_url = "http://sockclubcolormachine.appspot.com/bmp_serve_key/" + \
                str(design_entities[i].key.urlsafe())
            data = {'bmp': design_url, 'filename': str(
                filename_num), 'topColor': top_form_data, 'toeColor': toe_form_data, 'heelColor': heel_form_data, 'deckNumber': str(deck_id)}
            logging.info(data)
            response = awslambda.invoke(FunctionName='arn:aws:lambda:us-east-1:981532365545:function:deck_folder_out',
                                        InvocationType='RequestResponse', Payload=json.dumps(data))

            result = json.loads(response.get('Payload').read())
            if result.has_key("body"):
                pdf_images.append(result['body']['page1'])
                pdf_images.append(result['body']['page2'])

        response2 = awslambda.invoke(FunctionName='arn:aws:lambda:us-east-1:981532365545:function:zip_s3_folder',
                                     InvocationType='RequestResponse', Payload=json.dumps({"folder": str(deck_id)}))

        pp = os.path.join(os.path.dirname(__file__),
                          'templates', "pdf_page.html")
        page = template.render(
            pp, {'pdf_images': pdf_images, "pdf_filename": pdf_filename})
        self.response.out.write(page)


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/will_it_knit', KnitPage),
    ('/bitmap_builder', ArgyleBitmapBuilderPage),
    ('/lambda', LambdaPage),
    ('/deck_creation', DeckCreationPage),
    ('/fsb_image', FSBImagePage),
    ('/bitmap_upload', BitmapUploadPage),
    ('/pdf_creation', PdfDeckCreation),
    ('/zip_creation', ZipDeckCreation),
    ('/pdf_test', PDFTest),
    webapp2.Route(r'/img_serve/<colorways_id:\d+>/<sock_id:\d+>',
                  handler=ImgServe),
    webapp2.Route(r'/bmp_serve/<resource:\d+>',
                  handler=BmpServe),
    webapp2.Route(r'/bmp_serve_key/<resource:(.*)>',
                  handler=BmpServeKey),
    webapp2.Route(r'/bmp_serve_deck/<deck_id:\d+>/<design_id:\d+>',
                  handler=BmpServeDeck),
    webapp2.Route(r'/file_upload', handler=FileUpload),
    webapp2.Route(r'/design_serve/<resource:(.*)>', handler=DesignServe),
    webapp2.Route(r'/deck/<resource:(.*)>', handler=DeckPage),
], debug=True)
