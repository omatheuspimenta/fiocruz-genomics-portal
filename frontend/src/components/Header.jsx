// frontend/src/components/Header.jsx
import React from 'react';
import Icon from './Icon';
import IconLogo from './IconLogo'; // Import your new component

const Header = () => {
    return (
        <header className="bg-[#0f172a] text-white border-b border-slate-800 sticky top-0 z-50 shadow-lg">
            <div className="max-w-7xl mx-auto px-4 py-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        
                        {/* Use the new component here */}
                        {/* 'text-white' ensures the logo is white */}
                        <IconLogo className="h-12 w-auto text-white" />
                        
                        <div className="h-8 w-px bg-slate-700 mx-1 hidden sm:block"></div>

                        <div>
                            <h1 className="text-xl font-bold tracking-tight leading-none">Fiocruz Browser</h1>
                            <p className="text-xs text-slate-400 mt-1 font-light tracking-wide uppercase">Genomic Analytics Platform</p>
                        </div>
                    </div>
                    <div className="hidden md:flex items-center gap-4 text-sm text-slate-400">
                        <span className="flex items-center gap-1"><Icon name="database" size={14} /> Connected</span>
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;