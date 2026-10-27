import {initFilter} from './filter.js';
import {initLikes} from './likes.js';
import {initPosts} from './posts.js';

const feed = document.querySelector('.feed');
initLikes(feed);
initPosts(feed);
initFilter();
