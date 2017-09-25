class CPParser:
    def parse_user(self, content):
        videos_info = {}
        raw_user_video_infos = self.CP_REGS['user_video_info'].findall(content)
        for raw_video_info in raw_user_video_infos:
            view_id = raw_video_info[1]
            img_url = raw_video_info[2]
            title = raw_video_info[-1]
            vno = self.CP_REGS['vno'].findall(str(img_url))[0]
            videos_info[view_id] = {
                'view_id': view_id,
                'title': title,
                'vno': vno,
                'img_url': img_url,
            }

        return videos_info

    def parse_lists(self, content):
        videos_info = {}
        raw_video_infos = self.CP_REGS['list_video_info'].findall(content)

        for raw_video_info in raw_video_infos:
            view_id = raw_video_info[1]
            img_url = raw_video_info[3]
            title = raw_video_info[5]
            vtime = raw_video_info[7]
            user_no = raw_video_info[10]
            user_name = raw_video_info[12]
            vno = re.compile('_([\w\W]*?)\.').findall(str(img_url))[0]

            videos_info[view_id] = {
                'view_id': view_id,
                'title': title,
                'vtime': vtime,
                'vno': vno,
                'user_name': user_name,
                'user_no': user_no,
                'img_url': img_url
            }
        return videos_info

    def get_detail(self, content):
        content = str(content)
        video_info = {
            'vno': self.CP_REGS['content_vno'].findall(content)[0],
            'title': self.CP_REGS['title'].findall(content)[0],
            'vid': self.CP_REGS['vid'].findall(content)[0],
            'view_id': self.CP_REGS['content_view_id'].findall(content)[0],
            'user_no': int(self.CP_REGS['user'].findall(content)[0][1].strip()),
            'user_name': self.CP_REGS['username'].findall(content)[0].strip(),
            'download_url': self.CP_REGS['url'].findall(content)[0],
            'vtime': self.CP_REGS['time'].findall(content)[0].strip(),
        }

        return video_info