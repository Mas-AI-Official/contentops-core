import React from 'react'
import { Heart, MessageCircle, Share2, Music2, User } from 'lucide-react'

export default function MobilePreview({
    videoUrl,
    caption = "Check out this amazing video! #viral #content",
    accountName = "ContentCreator",
    likes = "12.5K",
    comments = "128",
    shares = "450"
}) {
    return (
        <div className="relative mx-auto border-gray-800 dark:border-gray-800 bg-gray-800 border-[14px] rounded-[2.5rem] h-[600px] w-[300px] shadow-xl">
            <div className="w-[148px] h-[18px] bg-gray-800 top-0 rounded-b-[1rem] left-1/2 -translate-x-1/2 absolute z-10"></div>
            <div className="h-[32px] w-[3px] bg-gray-800 absolute -left-[17px] top-[72px] rounded-l-lg"></div>
            <div className="h-[46px] w-[3px] bg-gray-800 absolute -left-[17px] top-[124px] rounded-l-lg"></div>
            <div className="h-[46px] w-[3px] bg-gray-800 absolute -left-[17px] top-[178px] rounded-l-lg"></div>
            <div className="h-[64px] w-[3px] bg-gray-800 absolute -right-[17px] top-[142px] rounded-r-lg"></div>

            <div className="rounded-[2rem] overflow-hidden w-full h-full bg-black relative">
                {/* Video Player */}
                {videoUrl ? (
                    <video
                        src={videoUrl}
                        className="w-full h-full object-cover"
                        autoPlay
                        loop
                        muted
                        playsInline
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gray-900 text-gray-500">
                        <p>No Video Preview</p>
                    </div>
                )}

                {/* Overlay UI */}
                <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent pt-20">
                    <div className="flex justify-between items-end">
                        <div className="text-white space-y-2 flex-1 mr-8">
                            <div className="font-bold flex items-center gap-2">
                                <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-black">
                                    <User className="w-5 h-5" />
                                </div>
                                @{accountName}
                            </div>
                            <p className="text-sm line-clamp-2">{caption}</p>
                            <div className="flex items-center gap-2 text-xs opacity-80">
                                <Music2 className="w-3 h-3" />
                                <span>Original Sound - {accountName}</span>
                            </div>
                        </div>

                        <div className="flex flex-col gap-4 items-center text-white">
                            <div className="flex flex-col items-center gap-1">
                                <div className="p-2 bg-gray-800/50 rounded-full">
                                    <Heart className="w-6 h-6 fill-white" />
                                </div>
                                <span className="text-xs font-bold">{likes}</span>
                            </div>
                            <div className="flex flex-col items-center gap-1">
                                <div className="p-2 bg-gray-800/50 rounded-full">
                                    <MessageCircle className="w-6 h-6 fill-white" />
                                </div>
                                <span className="text-xs font-bold">{comments}</span>
                            </div>
                            <div className="flex flex-col items-center gap-1">
                                <div className="p-2 bg-gray-800/50 rounded-full">
                                    <Share2 className="w-6 h-6 fill-white" />
                                </div>
                                <span className="text-xs font-bold">{shares}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
