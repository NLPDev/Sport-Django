from unittest import mock

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from rest_framework import status
from rest_framework.test import APITestCase

from multidb_account.videos.models import Video, VIDEO_YOUTUBE, VIDEO_VIMEO
from rest_api.tests import ApiTests
from rest_api.utils import get_youtube_video_id_from_url, get_vimeo_video_id_from_url, \
    grab_video_name_from_url, grab_video_url_from_embed_code

UserModel = get_user_model()


class VideoTests(ApiTests):

    @mock.patch('rest_api.utils.urlopen')
    def test_video_multiple_create(self, mocked_urlopen):
        user = self.coach_ca
        auth = 'JWT {}'.format(user.token)
        url = reverse_lazy('rest_api:video-list', kwargs={'uid': user.id})

        init_count = Video.objects.using(user.country).count()

        mocked_youtube_response = bytearray("""
            "itct":"CAMQu2kiEwjw8c7I-4HWAhXJyhgKHWVhDIso-B0=","cid":"8404786","adsense_video_doc_id":"yt_XpASSx0ecTU",
            "core_dbp":"ChZJczB0QmRtNGhsMEdzQnBkQmtTeWJREAEgASgA","hl":"ru_RU","plid":"AAVYD7kWl56Yfsvd",
            "ptk":"youtube_multi","ldpj":"-20","title":"Dragon Force - Through the Fire and Flames - Tina S Cover",
            "mpvid":"yktfwfB9sV_7-QLc","allow_below_the_player_companion":true,"video_id":"XpASSx0ecTU","cr":"RU",
            "t":"1","videostats_playback_base_url":"https:\/\/s.youtube.com\/api\/stats\/playback?el=detailp
            age\u0026ei=DEOoWfC7F8mVY-XCsdgI\u0026fexp=23700224%2C23700288%2C23700611%2C23701608%2C9405987%2C
            9422596%2C9431754%2C9440171%2C9449243%2C9453653%2C9461314%2C9463829%2C9467503%2C9474594%2C9475693%2C947
            6327%2C9478523%2C9479323%2C9480475%2C9480793%2C9484222%2C9486300%2C9487182%2C9488038%2C9489114%2C948928
            1%2C9489706%2C9489924\u0026vm=CAIQARgC\u0026plid=AAVYD7kWl56Yfsvd\u0026ns=yt\u0026c
        """, encoding='utf8')
        mocked_urlopen.return_value.read.return_value = mocked_youtube_response

        response = self.client.post(url, [
            {'url': 'https://www.youtube.com/watch?v=XpASSx0ecTU'},
            {'url': 'https://vimeo.com/177000555'}
        ], format='json', HTTP_AUTHORIZATION=auth)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.json())

        self.assertEqual(init_count + 2, Video.objects.using(user.country).count())

    @mock.patch('rest_api.utils.urlopen')
    def test_video_crud(self, mocked_urlopen):
        user = self.coach_ca
        user2 = self.athlete_ca
        auth = 'JWT {}'.format(user.token)
        auth2 = 'JWT {}'.format(user2.token)
        url = reverse_lazy('rest_api:video-list', kwargs={'uid': user.id})

        mocked_youtube_response = bytearray("""
            "itct":"CAMQu2kiEwjw8c7I-4HWAhXJyhgKHWVhDIso-B0=","cid":"8404786","adsense_video_doc_id":"yt_XpASSx0ecTU",
            "core_dbp":"ChZJczB0QmRtNGhsMEdzQnBkQmtTeWJREAEgASgA","hl":"ru_RU","plid":"AAVYD7kWl56Yfsvd",
            "ptk":"youtube_multi","ldpj":"-20","title":"Dragon Force - Through the Fire and Flames - Tina S Cover",
            "mpvid":"yktfwfB9sV_7-QLc","allow_below_the_player_companion":true,"video_id":"XpASSx0ecTU","cr":"RU",
            "t":"1","videostats_playback_base_url":"https:\/\/s.youtube.com\/api\/stats\/playback?el=detailp
            age\u0026ei=DEOoWfC7F8mVY-XCsdgI\u0026fexp=23700224%2C23700288%2C23700611%2C23701608%2C9405987%2C
            9422596%2C9431754%2C9440171%2C9449243%2C9453653%2C9461314%2C9463829%2C9467503%2C9474594%2C9475693%2C947
            6327%2C9478523%2C9479323%2C9480475%2C9480793%2C9484222%2C9486300%2C9487182%2C9488038%2C9489114%2C948928
            1%2C9489706%2C9489924\u0026vm=CAIQARgC\u0026plid=AAVYD7kWl56Yfsvd\u0026ns=yt\u0026c
        """, encoding='utf8')

        mocked_vimeo_response = bytearray("""
            window.vimeo = window.vimeo || {};
            window.vimeo.clip_page_config = {"clip":{"id":177000555,"title":"Sailor Moon S1 Ep1","description":null,
            "uploaded_on":"2016-07-31 21:40:35","uploaded_on_relative":"1 year ago","uploaded_on_full":"Sunday, July
            31, 2016 at 9:40 PM EST","is_spatial":false,"privacy":{"is_public":true,"type":"anybody","description":
            "Public"},"duration":{"raw":1288,"formatted":"21:28"},"is_liked":false,"is_unavailable":false,
            "likes_url":"\/177000555\/likes","is_live":false},"owner":{"id":54980022,"display_name":
            "Sailor Moon Generation","account_type":"","badge":null,"po
        """, encoding='utf8')

        vimeo_embed_code = """
            <iframe src="https://player.vimeo.com/video/177000555" width="640" height="480" frameborder="0"
            webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>
            <p><a href="https://vimeo.com/177000555">Sailor Moon S1 Ep1</a> from
            <a href="https://vimeo.com/user54980022">Sailor Moon Generation</a> on
            <a href="https://vimeo.com">Vimeo</a>.</p>
        """

        # POST incorrect data: empty
        response = self.client.post(url, {}, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST incorrect data #2: bad domain
        data = {'url': 'https://www.youtube.org/XpASSx0ecTU'}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST incorrect data #3: bad domain
        data = {'url': 'https://vimeo.org/177000555'}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST correct data
        video_url = 'https://www.youtube.com/watch?v=XpASSx0ecTU'
        video_name = 'Dragon Force - Through the Fire and Flames - Tina S Cover'
        data = {'url': video_url}
        mocked_urlopen.return_value.read.return_value = mocked_youtube_response

        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        video = Video.objects.using(user.country).get(pk=response.data['id'])
        self.assertEqual(video.user, user)
        self.assertIn(video.video_id, data['url'])
        self.assertEqual(video.video_id, 'XpASSx0ecTU')
        self.assertEqual(video.video_type, VIDEO_YOUTUBE)
        self.assertEqual(video.video_name, video_name)

        # POST correct data by user2
        video_name = 'Sailor Moon S1 Ep1'
        data = {'url': vimeo_embed_code}
        mocked_urlopen.return_value.read.return_value = mocked_vimeo_response

        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=auth2)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['video_name'], video_name)

        video2 = Video.objects.using(user2.country).get(pk=response.data['id'])
        self.assertEqual(video2.video_id, '177000555')
        self.assertEqual(video2.video_type, VIDEO_VIMEO)
        self.assertEqual(video2.video_name, video_name)

        # GET all videos of user1
        url = reverse_lazy('rest_api:video-list', kwargs={'uid': user.id})

        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # GET video of user2 by user1: 404
        url2 = reverse_lazy('rest_api:video-detail', kwargs={'uid': user.id, 'pk': video2.pk})
        response = self.client.get(url2, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # GET video of user1
        url = reverse_lazy('rest_api:video-detail', kwargs={'uid': user.id, 'pk': video.pk})
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], video.id)
        self.assertEqual(response.data['user'], user.id)
        self.assertEqual(response.data['video_id'], video.video_id)
        self.assertEqual(response.data['video_type'], video.video_type)
        self.assertEqual(response.data['video_name'], video.video_name)

        # PUT incorrect data: empty
        response = self.client.put(url, {}, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # PUT incorrect data: bad url
        data = {'url': 'bad url'}
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # PUT incorrect data #2
        youtube_video_id = 'XpASSx0ecTU'
        data = {
            'user': user.id,
            'video_type': '',
            'video_id': youtube_video_id,
            'date_added': video.date_added.isoformat(),
        }
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # PUT correct data
        old_video_id = video.video_id
        video_id = '177000555'
        data = {'url': ('https://vimeo.com/%s' % video_id)}
        response = self.client.put(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        video.refresh_from_db()
        self.assertEqual(video.video_id, video_id)
        self.assertNotEqual(video.video_id, old_video_id)
        self.assertEqual(video.video_type, VIDEO_VIMEO)

        # PATCH incorrect data: empty
        response = self.client.patch(url, {}, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # PATCH incorrect data #2
        data = {'video_type': 'dailymotion'}
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # PATCH incorrect data #3: bad url
        data = {'url': 'bad url'}
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # PATCH correct data
        old_video_id = video.video_id
        video_id = 'XpASSx0ecTU'
        youtube_video_url_2 = 'https://www.youtube.com/watch?v=%s' % video_id
        youtube_video_name_2 = 'Dragon Force - Through the Fire and Flames - Tina S Cover'

        data = {'url': youtube_video_url_2}
        mocked_urlopen.return_value.read.return_value = mocked_youtube_response

        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        video.refresh_from_db()
        self.assertEqual(video.video_id, video_id)
        self.assertEqual(video.video_name, youtube_video_name_2)
        self.assertNotEqual(video.video_id, old_video_id)
        self.assertEqual(video.video_type, VIDEO_YOUTUBE)

        # PUT incorrect video (of another owner)
        url2 = reverse_lazy('rest_api:video-detail', kwargs={'uid': user.id, 'pk': video2.pk})

        video_id = '177000555'
        data = {'url': ('https://vimeo.com/%s' % video_id)}
        response = self.client.put(url2, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # PATCH incorrect video (of another owner)
        response = self.client.patch(url2, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # DELETE incorrect video (of another owner)
        response = self.client.delete(url2, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # DELETE correct video (ours)
        response = self.client.delete(url, data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check total http request count
        self.assertEqual(mocked_urlopen.call_count, 4)


class UtilsTests(APITestCase):
    def test_get_youtube_video_id_from_url(self):
        exp_video_id = '5Y6HSHwhVlY'
        id_urls = (
            ('http://www.youtube.com/watch?v=%s' % exp_video_id),
            ('http://www.youtube.com/watch?/watch?other_param&v=%s' % exp_video_id),
            ('http://www.youtube.com/v/%s' % exp_video_id),
            ('http://youtu.be/%s' % exp_video_id),
            ('http://www.youtube.com/embed/%s?rel=0" frameborder="0"' % exp_video_id),
            ('http://m.youtube.com/v/%s' % exp_video_id),
            ('https://www.youtube-nocookie.com/v/%s?version=3&amp;hl=en_US' % exp_video_id),
        )

        no_id_urls = (
            'http://www.youtube.com/',
            'http://www.youtube.com/?feature=ytca',
        )

        for url in id_urls:
            got_video_id = get_youtube_video_id_from_url(url)
            self.assertEqual(exp_video_id, got_video_id)

        for url in no_id_urls:
            got_video_id = get_youtube_video_id_from_url(url)
            self.assertIsNone(got_video_id)

    def test_get_vimeo_video_id_from_url(self):
        exp_video_id = '88888888'
        urls = (
            ('http://vimeo.com/%s' % exp_video_id),
            ('http://player.vimeo.com/video/%s' % exp_video_id),
            ('http://vimeo.com/channels/staffpicks/%s' % exp_video_id),
            ('https://vimeo.com/groups/name/videos/%s' % exp_video_id),
            ('https://vimeo.com/album/2222222/video/%s' % exp_video_id),
        )

        for url in urls:
            got_video_id = get_vimeo_video_id_from_url(url)
            self.assertEqual(exp_video_id, got_video_id)

    def test_grab_video_name_from_url(self):
        exp_video_name = 'Sailor Moon S1 Ep1'
        url = 'https://vimeo.com/177000555'

        with mock.patch('rest_api.utils.urlopen') as mocked:
            mocked.return_value.read.return_value = bytearray(
                '<iframe src=\"https://player.vimeo.com/video/177000555\" width=\"640\" height=\"480\" '
                'frameborder=\"0\" webkitallowfullscreen mozallowfullscreen allowfullscreen><\/iframe>",'
                '"default_to_hd":0,"title":"Sailor Moon S1 Ep1","url":"https://vimeo.com/177000555",'
                '"privacy":"anybody","owner":{"account_type":"basic","name":"Sailor Moon Generation","img":'
                '"https://i.vimeocdn.com/portrait/14641238_60x60.jpg","url":"https://vimeo.com/user54980022",'
                '"img_2x":"https://i.vimeocdn.com/portrait/14641238_120x120.jpg","id":54980022',
                encoding='utf8'
            )
            got_video_name = grab_video_name_from_url(url)

        self.assertEqual(exp_video_name, got_video_name)

    def test_grab_video_url_from_embed_code(self):
        vimeo_embed_code = """
            <iframe src="https://player.vimeo.com/video/177000555" width="640" height="480" frameborder="0"
            webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>
            <p><a href="https://vimeo.com/177000555">Sailor Moon S1 Ep1</a> from
            <a href="https://vimeo.com/user54980022">Sailor Moon Generation</a> on
            <a href="https://vimeo.com">Vimeo</a>.</p>
        """

        url = grab_video_url_from_embed_code(vimeo_embed_code)
        self.assertEqual(url, 'https://vimeo.com/177000555')

        youtube_embed_code = """
            <iframe width="560" height="315" src="https://www.youtube.com/embed/XpASSx0ecTU" frameborder="0"
            allowfullscreen></iframe>
        """

        url = grab_video_url_from_embed_code(youtube_embed_code)
        self.assertEqual(url, 'https://www.youtube.com/embed/XpASSx0ecTU')
